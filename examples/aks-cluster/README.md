# Azure AKS Cluster Stack

## AKS with node pool

```
hubctl stack init -f hub.yaml
hubctl stack deploy
```

The stack will require the following parameters:

* `aksNodePool.nodeCount` number of nodes in the pool
* `aksNodePool.vmSize` size of the AKS VM (`Standard_D2_v2` is default)
