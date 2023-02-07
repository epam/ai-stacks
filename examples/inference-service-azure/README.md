# Example TorchServe InferenceService on KServe and AKS

## Prerequisites

* Deploy [AKS with Node Pool](https://github.com/epam/hub-kubeflow-stacks/tree/develop/examples/aks-cluster) stack (if needed)
* Deploy [Serving Stack](https://github.com/epam/hub-kubeflow-stacks/tree/develop/serving-azure) with [KServe](https://kserve.github.io/website/0.10/) on top of AKS instance provisioned by `AKS with Node Pool` stack or other AKS instance

## Inference Service deployment and example request

1. Create Kubernetes namespace for the Inference Service: `kubectl create ns serving-example` and switch to that namespace
2. Run `kubectl -n serving-example apply -f image-classifier.yaml` to deploy the Inference Service.
3. Run `kubectl -n serving-example get inferenceservice image-classifier` to verify that the service has been successfully deployed: `READY` column of the Inference Service instance must be `True`. 
4. Run `kubectl -n serving-example port-forward service/image-classifier-predictor-default 8081:80` to port forward the service and call it directly from your computer.
5. The ML model deployed to the Inference Service can recognize handwritten digits from 0 to 9. There are [0.json](0.json) and [1.json](1.json) files in this dirrectory, which are `base64` encoded represenations of handwritten numbers [0](0.png) and [1](1.png). 
6. Run `curl -v http://localhost:8081/v1/models/mnist:predict -d @./0.json` to predict which digit the `0.json` file represents. The service should respond something similar to:

```
{
  "predictions": [
    0
  ]
}
```

## Cleanup

Run `kubectl -n serving-example delete -f image-classifier.yaml` to undeploy the Inference Service. Undeploy `Serving Stack` and `AKS with Node Pool` stacks if needed.
