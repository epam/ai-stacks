# Profiles Operastor

We want to provide some consistency when new kubeflow profiles has been created.
Such as enforcing quota, istio settings, pod defaults or anything that we don't know about
## Functionality

There is a configap that has been referenced as `CONFIG_DIR` environment variable (can be found in: `kustomize/base/conf'`). This contains manifests that will be merged with the resoruce (if exists) or create new resource (if not).

User can define their own configs, by creating an overlay for kustomize (yes, this component has been deployed with kustomize) and provide new resources as `merge` for configmap `manifests`. See
`kustomize/skaffold` for inspiration
### Installation instructions

#### With hub CLI

`This` operator can be installed as hub component. Just add it in the runlist behind `kubeflow`. In this case `kubeflow` will produce all necessary parameters that will be accepted as meaningful defaults by `this` component

## Prerequisite

* hub-cli
* kubectl
* kustomize

###  Prerequisites

Following tools has been used

1. Skaffold
2. Python v3.8+ (with `venv`)
3. Kopf (comes as runtime dependency)
4. VS Code (IDE used for development)

In your terminal:
```bash
python3 -m venv ".venv"
source ".venv/bin/activate"
pip3 install --upgrade pip
pip3 install -r requirements.txt -r requirements.dev.txt
```

###  Testing

To see available tests
```bash
pytest --collect-only
```

To run tests
```bash
pytest src
```

To run tests from vscode in debug
0. Apply following settings on folder level
```json
{
  "python.testing.unittestArgs": ["-v", "-s", "src", "-p","test_*.py"],
  "python.testing.pytestEnabled": true,
}
```
1. Run task: `Python: Debug all Tests`

### Integration Tests

To be implemented when logic of the operator will become more complex. (see: https://kopf.readthedocs.io/en/stable/testing/)

### Setup GHCR

* Generate access token to: https://github.com/settings/tokens/new?scopes=write:packages
  
  > You need to setup: `write:packages` scope to be able to push images to GHCR. For more info [here](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

* Save it as `GITHUB_TOKEN` in your environment (see below)

* GHCR image can be viewed here: https://github.com/orgs/epam/packages/container/package/hub-kubeflow-stacks%2Freplikate

```bash
export GITHUB_TOKEN="your token" 
echo "$GITHUB_TOKEN" | docker login "ghcr.io" -u "akranga" --password-stdin

export SKAFFOLD_DEFAULT_REPO="ghcr.io/epam/hub-kubeflow-stacks"
```

### Environment variables

Setup skaffold defaults:
```bash
# private repo will have different default repo
export SKAFFOLD_PROFILE="local"
export SKAFFOLD_NAMESPACE="default"
export SKAFFOLD_CACHE_ARTIFACTS="default"
export SKAFFOLD_CACHE_ARTIFACTS="true"
```

### Remote debug

Configmap `k8s/development.yaml` will source the configuration. Please note that `DEBUG_ENABLED=1` means that operator will wait for PTVSD connectivity via port `9229`
( For details, see `profiles-operator attach` from `.vscode/launch.json`)

1. In your terminal: `skaffold debug` or `skaffold dev`
2. In your VS Code: Debug >> `profiles-operator attach`
3. Wait for the attachment
4. To test
```bash
kubectl apply -f test/profile1.yaml
kubectl get -f test/profile1.yaml -o yaml | yq e -C '.spec' -
```

### Local debug

0. Update `setting.json`

```json
{
  "name": "profiles: attach localhost",
  "type": "python",
  "request": "attach",
  "localRoot": "${workspaceRoot}",
  "port": 9229,
  "host": "localhost"
}
```

1. declare environemnt variable `REMOTE_DEBUG=true`
2. run following command

```bash
kopf run main.py --log-format=plain --dev --standalone
```

It will stop waiting for you to attach with `PTVSD`

3. Launch debug task: `profiles: attach localhost`

