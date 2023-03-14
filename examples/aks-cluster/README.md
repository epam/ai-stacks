# Azure AKS Cluster Stack with Kubernetes Tools

The stack deploys AKS cluster with pre-configured [Certificate](https://cert-manager.io/), [DNS Manager](https://github.com/kubernetes-sigs/external-dns) and [Ingress Controller](https://docs.nginx.com/nginx-ingress-controller/) components.

It also deploys free publicly resolvable DNS Zone under `epam.devops.delivery` domain name and configures the components to use this zone (`ingress` hostnames, DNS challenges, etc.)
 
## Prerequisites

### To deploy the stack a user must have the following tools:

* [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
* [hubctl](https://superhub.io/)
* [terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
* [helm](https://helm.sh/docs/intro/install/)
* [jq](https://stedolan.github.io/jq/download/)
* [yq (golang veriosn)](https://stedolan.github.io/jq/download/)

### Azure requirements:

* Users should have an active Azure subscription and at least one Resource Group
* Users should have cloud permissions to create and manage AKS Clusters, DNS Zones and Storage Accounts. Permissions to create Roles or assign permissions to roles are not required.
* <b>To deploy the stack users should pre-create an Azure Service Principal (App Registration) and assign `DNS Contributor` role to that principal.</b> The Service Principal will be used to authorize the Azure Cloud DNS API requests of Certificate and DNS manager components.

## Deployment instructions

