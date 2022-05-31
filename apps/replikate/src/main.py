#!/usr/bin/env python3
import asyncio
import kopf
import pykube
import logging
import yaml
from os import environ, path
from jinja2 import Environment, FileSystemLoader
from glob import glob

environ.setdefault("MANIFESTS_SOURCE", "replikate-operator-manifests")
environ.setdefault("INSTANCE_ID", "kubeflow-replikdate")
environ.setdefault("POLL_INTERVAL", "300")
environ.setdefault("REMOTE_DEBUG", "disabled")

CONFIGMAP     = environ["MANIFESTS_SOURCE"]
CONFIG_DIR    = environ["CONFIG_DIR"]
INSTANCE_ID   = environ["INSTANCE_ID"]
INTERVAL      = float(environ["INTERVAL"])

FILTER_LABEL={"app.kubernetes.io/part-of": "kubeflow-profile"}

logging.info(f"Starging operator '{INSTANCE_ID}'...")
if environ["REMOTE_DEBUG"] == "enabled":
  import ptvsd
  logging.info("Opened debug port 9229")
  logging.info("Waiting to attach...")
  ptvsd.enable_attach(address=('0.0.0.0', 9229))
  ptvsd.wait_for_attach()


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


@kopf.timer(
  'v1', 'namespaces', labels={f"superhub.io/{INSTANCE_ID}": "enabled"}, initial_delay=120.0, interval=INTERVAL,
)
@kopf.on.create('namespaces', labels={f"superhub.io/{INSTANCE_ID}": "enabled"}|FILTER_LABEL,)
@kopf.on.update('namespaces', labels={f"superhub.io/{INSTANCE_ID}": "enabled"}|FILTER_LABEL,)
@kopf.on.resume('namespaces', labels={f"superhub.io/{INSTANCE_ID}": "enabled"}|FILTER_LABEL,)
def reconcile(logger, name, spec, body, patch, **_):
  """
  Triggered on profile change or periodically
  ---
  Syncronies the resourcess describes as templates and propagate it to the profile
  """
  logger.info(f"Reconciling {name}")
  owner  = spec.get("owner", {}).get("name")
  params = {"name": name, "owner": owner}
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

    kopf.adopt(data)
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


@kopf.on.create('v1', 'namespaces', labels={f"superhub.io/{INSTANCE_ID}": kopf.ABSENT}|FILTER_LABEL,)
@kopf.on.update('v1', 'namespaces', labels={f"superhub.io/{INSTANCE_ID}": kopf.ABSENT}|FILTER_LABEL,)
@kopf.on.resume('v1', 'namespaces', labels={f"superhub.io/{INSTANCE_ID}": kopf.ABSENT}|FILTER_LABEL,)
def add_instance_label(name, logger, patch, **_):
  logger.info(f"Starting to watch {name}")
  kopf.label(patch, {f"superhub.io/{INSTANCE_ID}": "enabled"})


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
  global api, config
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
    raise ValueError("Unsupported auth method")
  api = pykube.HTTPClient(config)

@kopf.on.login(errors=kopf.ErrorsMode.PERMANENT)
async def init_connection(logger, **_):
  ca = config.cluster.get('certificate-authority')
  cert = config.user.get('client-certificate')
  pkey = config.user.get('client-key')
  token = config.user.get('token')
  # Handling case if EKS
  if not cert and not pkey and not token:
    exec = config.user.get('exec')
    # check if eks
    if exec and exec.get('apiVersion') == 'client.authentication.k8s.io/v1alpha1':
      cluster = exec.get('args')[-1]
      if cluster:
        logger.info(f"Getting auth token for eks cluster {cluster}")
        from eks_token import get_token
        token = get_token(cluster_name=cluster)['status']['token']

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
