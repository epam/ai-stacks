# Azure AKS Cluster Stack with Kubernetes Tools

The stack deploys AKS cluster with pre-configured [Certificate](https://cert-manager.io/), [DNS Manager](https://github.com/kubernetes-sigs/external-dns) and [Ingress Controller](https://docs.nginx.com/nginx-ingress-controller/) components.

It also deploys a free publicly resolvable DNS Zone under `epam.devops.delivery` domain name and configures the components to use this zone (`ingress` hostnames, DNS challenges, etc.)
 
## Prerequisites

### To deploy the stack user must have the following tools:

* [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
* [hubctl](https://superhub.io/)
* [terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
* [helm](https://helm.sh/docs/intro/install/)
* [jq](https://stedolan.github.io/jq/download/)
* [yq (golang veriosn)](https://stedolan.github.io/jq/download/)

### `hubctl` extensions

Please install `hubctl` extensions using the following command:
```
hubctl extensions install
```
By default, the extensions are downloaded to the `$HOME/.hub` directory.

NOTE: The extensions are in active development. To use the latest updates of the extensions please `cd` to `$HOME/.hub` and switch to the `develop` branch: `git checkout develop`

### Azure requirements:

* Users should have an active Azure subscription and at least one Resource Group
* Users should have cloud permissions to create and manage AKS Clusters, DNS Zones, and Storage Accounts. Permissions to create Roles or assign permissions to roles are not required.
* <b>To deploy the stack users should pre-create an Azure Service Principal (App Registration) and assign `DNS Contributor` role to that principal.</b> The Service Principal will be used to authorize the Azure Cloud DNS API requests of Certificate and DNS manager components.

## Deployment instructions

Initialize a stack instance using the following command:
```
hubctl stack init
```
This will set up the stack environment and download stack components to the working directory of the stack.

Before the stack instance can be deployed we ask users to provide some configuration details about the stack being deployed. The details depend on the stack and are documented in the `hub.yaml` file of the stack. Run 

```
hubctl stack configure
```
to configure the stack.

Once the configuration is done run

```
hubctl stack deploy
```
to deploy the stack instance.
