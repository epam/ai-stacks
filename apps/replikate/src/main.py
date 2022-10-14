#!/usr/bin/env python3
import asyncio
from tkinter.messagebox import IGNORE
from datetime import timedelta
import kopf
import pykube
import logging
import yaml
from os import environ, path
from jinja2 import Environment, FileSystemLoader
from glob import glob
from kopf import not_
from pytimeparse.timeparse import timeparse
import subprocess
import json

def str_to_timedelta(value: str) -> timedelta:
  try:
    secs = float(value) * 60
  except ValueError:
    secs = timeparse(value)
  return timedelta(seconds=secs)

environ.setdefault("MANIFESTS_SOURCE", "replikate-operator-manifests")
environ.setdefault("INSTANCE_ID", "kubeflow-replikdate")
environ.setdefault("POLL_INTERVAL", "300")
environ.setdefault("REMOTE_DEBUG", "disabled")

CONFIGMAP     = environ.get("MANIFESTS_SOURCE")
CONFIG_DIR    = environ["CONFIG_DIR"]
INSTANCE_ID   = environ["INSTANCE_ID"]
INTERVAL      = str_to_timedelta(environ["INTERVAL"])
IGNORE_ANNOT  = f"superhub.io/{INSTANCE_ID}"

FILTER_LABEL={"app.kubernetes.io/part-of": "kubeflow-profile"}

IGNORE_NAMESPACES = []

logging.info(f"Starging operator '{INSTANCE_ID}'...")
if environ["REMOTE_DEBUG"] == "enabled":
  import ptvsd
  logging.info("Opened debug port 9229")
  logging.info("Waiting to attach...")
  ptvsd.enable_attach(address=('0.0.0.0', 9229))
  ptvsd.wait_for_attach()


@kopf.on.create('namespace')
@kopf.on.update('namespace')
@kopf.on.resume('namespace')
def update_ignore_namespace(logger, name, meta, **_) -> bool:
  """ Returns true if added to the ignore list """
  labels={**meta.get('labels', {}), **meta.get('annotations', {})}
  ignore_enabled = "enabled" == labels.get(IGNORE_ANNOT, "disabled")
  if ignore_enabled and name not in IGNORE_NAMESPACES:
    logger.info(f"Namespace {name} has ignore annotation, I will ignore all objects in it")
    IGNORE_NAMESPACES.append(name)
    return True
  elif ignore_enabled and name in IGNORE_ANNOT:
    logger.info(f"Namespace {name} has no more ignore annotation")
    IGNORE_NAMESPACES.remove(name)
  else:
    owner = [own for own in meta.get('ownerReferences', []) if own.get('kind') == 'Profile' and path.dirname(own.get('apiVersion', '')) == 'kubeflow.org']
    if not owner and name not in IGNORE_NAMESPACES:
      logger.info(f"Namespace {name} is not part of Kubeflow Profile, I will ignore all objects in it")
      IGNORE_NAMESPACES.append(name)
      return True
  return False


def load_templates(_=None):
  """Reads file content and stores it as a variable"""
  global TEMPLATES
  result = []
  # logging.info(f"Loading manifests from {dir}")
  jinja = Environment(loader=FileSystemLoader(CONFIG_DIR, followlinks=True))
  for file in glob(path.join(CONFIG_DIR, "*.yaml")):
    if path.isdir(file): continue
    try:
      t_name = path.relpath(file, CONFIG_DIR)
      template = jinja.get_template(t_name)
    except:
      logging.debug(f"* Skipping {file}")
      continue
    logging.info(f"* loading template: {file}")
    result.append(template)
  TEMPLATES = result


def namespace_ignored(name, **_) -> bool:
  return name in IGNORE_NAMESPACES

@kopf.timer('v1', 'namespaces', initial_delay=120.0, interval=INTERVAL, when=not_(namespace_ignored))
@kopf.on.create('namespaces', when=not_(namespace_ignored))
@kopf.on.update('namespaces', when=not_(namespace_ignored))
@kopf.on.resume('namespaces', when=not_(namespace_ignored))
def reconcile(logger, name, spec, body, patch, **_):
  """
  Triggered on profile change or periodically
  ---
  Syncronies the resourcess describes as templates and propagate it to the profile
  """
  logger.info(f"Reconciling {name}")
  self_obj = deep_merge({}, body)
  # logger.info(f" >> {type(self_obj)}")
  params = {"name": name, "this": self_obj}
  self_hash = k8s_hash(body)

  for tpl in TEMPLATES:
    txt = tpl.render(params)
    data = yaml.safe_load(txt)

    _hash = k8s_hash(data)
    if self_hash == _hash:
      # this is a special case. It seems user wants to change
      # the same object by template that we are watching
      diff = deep_merge(body, data)
      if diff:
        logger.info(f"Patching self {name}: {diff}")
        deep_merge(patch, diff)
      continue

    # see: https://github.com/nolar/kopf/issues/687
    # kopf.adopt(data)
    # for ref in data['metadata']['ownerReferences']:
    #   if ref.get('Kind') == body['kind'] and ref.get('Name') == name:
    #     ref['controller'] = False

    client = pykube.object_factory(api, data['apiVersion'], data['kind'])
    resource = client(api, data)
    if resource.exists():
      resource.reload()
      changed = deep_merge(resource.obj, data)
      if changed:
        logger.info(f"* {resource.kind.lower()}/{resource.name}: update {changed}")
        resource.update()
      else:
        logger.debug(f"* {resource.kind.lower()}/{resource.name}: already up to date")
    else:
      logger.info(f"* {resource.kind.lower()}/{resource.name}: creating")
      resource.create()


@kopf.on.create('v1', 'namespaces', labels={IGNORE_ANNOT: kopf.ABSENT}, when=not_(namespace_ignored))
@kopf.on.update('v1', 'namespaces', labels={IGNORE_ANNOT: kopf.ABSENT}, when=not_(namespace_ignored))
@kopf.on.resume('v1', 'namespaces', labels={IGNORE_ANNOT: kopf.ABSENT}, when=not_(namespace_ignored))
def add_instance_label(name, logger, patch, **_):
  logger.info(f"Starting to watch {name}")
  kopf.label(patch, {f"superhub.io/{INSTANCE_ID}": "enabled"})


if CONFIGMAP:
  logging.info(f"Whatching configmap {CONFIGMAP}")
  @kopf.on.update('configmaps', field='metadata.name', value='CONFIGMAP')
  def reload_templates(name, logger, **_):
    logger.info(f"Reloading: {CONFIG_DIR}")
    load_templates()


@kopf.on.startup()
async def startup_fn_simple(**_):
  global LOCK
  LOCK = asyncio.Lock()
  load_templates()
  # asyncio.create_task(watch_for_change())


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
  settings.posting.level = logging.WARNING
  settings.watching.connect_timeout = 1 * 60
  settings.watching.server_timeout = 10 * 60
  settings.scanning.disabled = True


@kopf.on.startup()
async def init_kubernetes_client(logger, **_):
  global api, config, Namespaces
  logger.info("Lading kubeconfig...")
  token = "/var/run/secrets/kubernetes.io/serviceaccount/token"
  kubeconfig = environ.get("KUBECONFIG")
  if path.isfile(token):
    logger.info(f'From token file: {token}')
    token_dir = path.dirname(token)
    config = pykube.KubeConfig.from_service_account(path=token_dir)
  elif kubeconfig:
    logger.info(f'From environment {kubeconfig}')
    config = pykube.KubeConfig.from_file(filename=kubeconfig)
  else:
    config = pykube.KubeConfig.from_file()

  # WORKAROUND: pukube doesn't know how to deal with null values in kubeconfig
  config.user.setdefault('exec', {})
  config.user['exec']['args'] = config.user['exec'].get('args') or []
  config.user['exec']['env'] = config.user['exec'].get('env') or []

  api = pykube.HTTPClient(config)
  nss = pykube.Namespace.objects(api).all()
  logger.info("Initializing namespaces...")
  for ns in nss:
    if update_ignore_namespace(logger, ns.name, ns.metadata,):
      logger.info(f"Ignoring namespace {ns.name}")


@kopf.on.login(errors=kopf.ErrorsMode.PERMANENT)
async def init_connection(logger, **_):
  ca = config.cluster.get('certificate-authority')
  cert = config.user.get('client-certificate')
  pkey = config.user.get('client-key')
  token = config.user.get('token')
  # Handling case if EKS
  if not cert and not pkey and not token:
    exec_conf = config.user.get('exec')
    if exec_conf.get('command'):
      logger.info("Retrieving token...")
      cmd_env_vars = dict(environ)
      for env_var in exec_conf.get("env") or []:
        cmd_env_vars[env_var["name"]] = env_var["value"]
      output = subprocess.check_output(
          [exec_conf["command"]] + exec_conf["args"], env=cmd_env_vars
      )
      parsed_out = json.loads(output)
      token = parsed_out["status"]["token"]
    # NOTE: temporrarilly disabled EKS case, we possibly can gateway with code above
    # else:
    #   logger.info("Retrieving ")
    #   cluster = exec_conf.get('args')[-1]
    #   if cluster:
    #     logger.info(f"Getting auth token for eks cluster {cluster}")
    #     from eks_token import get_token
    #     token = get_token(cluster_name=cluster)['status']['token']

  return kopf.ConnectionInfo(
      server=config.cluster.get('server'),
      ca_path=ca.filename() if ca else None,
      insecure=config.cluster.get('insecure-skip-tls-verify'),
      username=config.user.get('username'),
      password=config.user.get('password'),
      scheme='Bearer',
      token=token,
      certificate_path=cert.filename() if cert else None,
      private_key_path=pkey.filename() if pkey else None,
      default_namespace=config.namespace,
  )


def merge_list(accum, sample):
  diff = [x for x in sample if x not in accum]
  accum.extend(diff)
  return diff


def deep_merge(accum, sample):
  """
  Recursively merges a dictionary on the right to the accumulator on the left
  Returns merge difference (applied values to the accumulator)
  """
  result = {}
  for key, value in sample.items():
    if value == None: continue
    if isinstance(value, dict):
      if key not in accum: accum[key] = {}
      diff = deep_merge(accum[key], value)
      if diff: result[key] = diff
    if isinstance(value, list):
      if key not in accum: accum[key] = []
      diff = merge_list(accum[key], value)
      if diff: result[key] = diff
    else:
      if key not in accum:
        accum[key] = value
        result[key] = accum[key]
  return result


def k8s_hash(obj: dict) -> int:
  """ uses kind, apiVersion, name and namespace\
    to compute hash """

  # avoiding None as part of dict
  return hash("/".join([
      obj.get("apiVersion") or "",
      obj.get("kind") or "",
      obj.get("metadata", {}).get("namespace") or "",
      obj.get("metadata", {}).get("name") or ""
  ]))
