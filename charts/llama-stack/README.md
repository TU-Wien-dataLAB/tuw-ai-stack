# Llama Stack Helm Chart

This Helm chart is designed to install the Llama Stack with the TUW AI distribution, a comprehensive platform for LLM tasks.

The chart provides a convenient way to deploy and manage the Llama Stack on Kubernetes or OpenShift clusters. It offers flexibility in customizing the deployment by allowing users to modify values such as image repositories, probe configurations, resource limits, and more.

## Quick Start

The default configuration uses:
- Vector store: `faiss` (in-memory)
- Embedding model: `sentence-transformers/nomic-ai/nomic-embed-text-v1.5` (768 dimensions)

To deploy with defaults:

```sh
helm upgrade -i llama-stack charts/llama-stack
```

> [!TIP]
> Can be installed on [minikube](https://minikube.sigs.k8s.io/docs/start/?arch=%2Flinux%2Fx86-64%2Fstable%2Fbinary+download) for local validation.

## Configuration Architecture

The Llama Stack configuration is now **fully managed via Helm values** and mounted as a ConfigMap. This approach is more robust than relying on the Python package location which can change between versions.

```
┌─────────────────────────────────────┐
│         Helm Values                 │
│      (values.yaml)                  │
│   runConfig (complete run.yaml)     │
└──────────────┬──────────────────────┘
               │
               ▼ toYaml
┌─────────────────────────────────────┐
│       ConfigMap                     │
│  /etc/llama-stack/run.yaml          │
│  (All configuration in one place)   │
└──────────────┬──────────────────────┘
               │
               ▼ mounted as volume
┌─────────────────────────────────────┐
│     Llama Stack Container           │
│  RUN_CONFIG_PATH=/etc/llama-stack/  │
│                run.yaml             │
│  llama-stack version: 0.3.3         │
└─────────────────────────────────────┘
```

**Benefits:**
- ✅ Avoids Python version dependencies
- ✅ Makes configuration fully declarative via Helm
- ✅ Allows runtime configuration changes via Helm upgrades
- ✅ No need to rebuild Docker image for config changes
- ✅ Version pinned to llama-stack 0.3.3 for stability

## Customizing Configuration

**All configuration is done through the `runConfig` section in `values.yaml`**. This section contains the complete run.yaml that will be mounted as a ConfigMap.

### Example: Using vLLM Embeddings with Milvus

Create a `custom-values.yaml`:

```yaml
runConfig:
  vector_stores:
    default_provider_id: milvus
    default_embedding_model:
      provider_id: vllm
      model_id: intfloat/e5-mistral-7b-instruct
  registered_resources:
    models:
      - model_id: intfloat/e5-mistral-7b-instruct
        provider_id: vllm
        provider_model_id: intfloat/e5-mistral-7b-instruct
        model_type: embedding
        metadata:
          embedding_dimension: 4096
```

Deploy with:

```sh
helm upgrade -i llama-stack charts/llama-stack -f custom-values.yaml
```

Or via command line:

```sh
helm upgrade -i llama-stack charts/llama-stack \
  --set 'runConfig.vector_stores.default_provider_id=milvus' \
  --set 'runConfig.vector_stores.default_embedding_model.provider_id=vllm' \
  --set 'runConfig.vector_stores.default_embedding_model.model_id=intfloat/e5-mistral-7b-instruct'
```

### What You Can Customize

The entire `runConfig` section can be modified to:

- Change vector store providers (faiss, milvus, sqlite-vec, chromadb, pgvector, qdrant)
- Register embedding models with different dimensions
- Add new inference providers
- Configure safety shields
- Set up tool runtimes (Brave Search, Tavily, RAG, MCP)
- Modify storage backends
- Configure agents and batch processing

**Common embedding dimensions:**
- `nomic-ai/nomic-embed-text-v1.5` (sentence-transformers): 768
- `intfloat/e5-mistral-7b-instruct` (vllm): 4096
- `text-embedding-3-small` (openai): 1536
- `text-embedding-3-large` (openai): 3072

### Important: vLLM Auto-Registration

The vLLM provider config includes `allowed_models: []` to **prevent automatic model registration**. This is crucial because:

1. vLLM auto-discovers all models at the endpoint
2. Embedding models would be incorrectly registered as text completion models
3. This causes conflicts when you try to register them correctly as embedding models

**Solution**: Models are manually registered in `registered_resources.models` with the correct `model_type: embedding`. The empty `allowed_models` list prevents vLLM from auto-registering them.

See `values.yaml` for the complete default configuration structure.

## Values

### Llama Stack Specific

| Key                     | Type     | Default                                                                    | Description                                                                                                                           |
| :---------------------- | :------- | :------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| `customRunConfig`       | `bool`   | `false`                                                                    | Indicates whether a custom run configuration is being used.                                                                           |
| `distribution`          | `string` | `"distribution-remote-vllm"`                                               | Specifies the distribution or type of deployment being used (in this case, related to a remote vLLM distribution).                    |
| `telemetry.enabled`     | `bool`   | `false`                                                                    | Enables or disables telemetry collection.                                                                                             |
| `telemetry.serviceName` | `string` | `"otel-collector.openshift-opentelemetry-operator.svc.cluster.local:4318"` | The service name and address of the telemetry collector.                                                                              |
| `telemetry.sinks`       | `string` | `"console,sqlite,otel"`                                                    | Specifies the destinations or sinks where telemetry data will be sent.                                                                |
| `vllm.inferenceModel`   | `string` | `"llama2-7b-chat"`                                                         | The specific inference model to be used by vLLM (a high-throughput and memory-efficient inference service for large language models). |
| `vllm.url`              | `string` | `"http://vllm-server"`                                                     | The URL of the vLLM service.                                                                                                          |
| `env`                   | `object` | N/A                                                                        | A set of key/value pairs that can be set in the pod                                                                                   |

### General

| Key                                        | Type   | Default                                                                                                                            | Description                                                                                                                                                                                                                                                           |
| :----------------------------------------- | :----- | :----------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `autoscaling.enabled`                      | `bool` | `false`                                                                                                                              | Enables or disables horizontal pod autoscaling, which automatically adjusts the number of running instances based on CPU utilization.                                                                                                                             |
| `autoscaling.maxReplicas`                  | `int`  | `100`                                                                                                                                | The maximum number of pod replicas that the autoscaler can scale up to.                                                                                                                                                                                               |
| `autoscaling.minReplicas`                  | `int`  | `1`                                                                                                                                  | The minimum number of pod replicas that will always be running.                                                                                                                                                                                                      |
| `autoscaling.targetCPUUtilizationPercentage` | `int`  | `80`                                                                                                                                 | The target average CPU utilization across all running pods that the autoscaler will aim to maintain.                                                                                                                                                                    |
| `image.pullPolicy`                         | `string` | `"Always"`                                                                                                                           | Defines when to pull the Docker image for the container (e.g., always pull, pull if not present, etc.).                                                                                                                                                           |
| `image.repository`                         | `string` | `"docker.io/llamastack/{{ $.Values.distribution }}"`                                                                                 | The Docker image repository where the container image is located. It likely uses the `distribution` value to construct the full image path.                                                                                                                            |
| `image.tag`                                | `string` | `"0.1.6"`                                                                                                                            | The specific version tag of the Docker image to use.                                                                                                                                                                                                                 |
| `ingress.annotations`                      | `object` | `{}`                                                                                                                                 | Kubernetes Ingress annotations, which can be used to configure load balancers and other external access settings.                                                                                                                                                    |
| `ingress.className`                        | `string` | `""`                                                                                                                                 | The name of the Ingress controller to use for this Ingress resource.                                                                                                                                                                                                 |
| `ingress.enabled`                          | `bool` | `true`                                                                                                                               | Enables or disables the creation of a Kubernetes Ingress resource, which allows external access to the application.                                                                                                                                                  |
| `ingress.hosts[0].host`                    | `string` | `"chart-example.local"`                                                                                                            | The hostname that the Ingress will route traffic to. This is often a placeholder or example.                                                                                                                                                                             |
| `ingress.hosts[0].paths[0].path`          | `string` | `"/"`                                                                                                                                  | The path on the specified host that the Ingress will route traffic to (in this case, the root path).                                                                                                                                                                     |
| `ingress.hosts[0].paths[0].pathType`      | `string` | `"ImplementationSpecific"`                                                                                                         | The type of path matching used by the Ingress controller.                                                                                                                                                                                                            |
| `ingress.tls`                              | `list`   | `[]`                                                                                                                                 | Configuration for Transport Layer Security (TLS) termination at the Ingress, allowing for HTTPS.                                                                                                                                                                     |
| `livenessProbe.httpGet.path`               | `string` | `"/v1/health"`                                                                                                                      | The HTTP endpoint path that the liveness probe will check to determine if the container is running and healthy.                                                                                                                                                           |
| `livenessProbe.httpGet.port`               | `int`  | `5001`                                                                                                                               | The port that the liveness probe will connect to for the HTTP health check.                                                                                                                                                                                           |
| `podAnnotations`                           | `object` | `{}`                                                                                                                                 | Kubernetes Pod annotations, which can be used to attach arbitrary non-identifying metadata to the Pod.                                                                                                                                                                 |
| `podLabels`                                | `object` | `{}`                                                                                                                                 | Kubernetes Pod labels, which are key/value pairs that are attached to Pods and can be used for organizing and selecting groups of Pods.                                                                                                                                    |
| `podSecurityContext`                       | `object` | `{}`                                                                                                                                 | Defines the security context for the Pod, such as user and group IDs, security capabilities, etc.                                                                                                                                                                      |
| `readinessProbe.httpGet.path`              | `string` | `"/v1/health"`                                                                                                                      | The HTTP endpoint path that the readiness probe will check to determine if the container is ready to serve traffic.                                                                                                                                                           |
| `readinessProbe.httpGet.port`              | `int`  | `5001`                                                                                                                               | The port that the readiness probe will connect to for the HTTP readiness check.                                                                                                                                                                                          |
| `replicaCount`                             | `int`  | `1`                                                                                                                                  | The desired number of pod replicas to run.                                                                                                                                                                                                                         |
| `resources.limits.cpu`                     | `string` | `"100m"`                                                                                                                             | The maximum amount of CPU resources that a container can use (in millicores).                                                                                                                                                                                            |
| `resources.limits.memory`                  | `string` | `"500Mi"`                                                                                                                             | The maximum amount of memory that a container can use (in megabytes).                                                                                                                                                                                                  |
| `resources.requests.cpu`                   | `string` | `"100m"`                                                                                                                             | The amount of CPU resources that Kubernetes will guarantee to be available for the container.                                                                                                                                                                              |
| `resources.requests.memory`                | `string` | `"500Mi"`                                                                                                                             | The amount of memory that Kubernetes will guarantee to be available for the container (in megabytes).                                                                                                                                                                     |
| `route`                                    | `object` | `{"annotations":{},"enabled":false,"host":"","path":"","tls":{"enabled":true,"insecureEdgeTerminationPolicy":"Redirect","termination":"edge"}}` | Configuration for an OpenShift Route object, which is used for exposing services externally on OpenShift.                                                                                                                                                           |
| `route.annotations`                        | `object` | `{}`                                                                                                                                 | Additional custom annotations for the OpenShift Route object.                                                                                                                                                                                                        |
| `route.host`                               | `string` | `Set by OpenShift`                                                                                                                   | The hostname for the OpenShift Route. This is typically managed by OpenShift.                                                                                                                                                                                           |
| `route.path`                               | `string` | `""`                                                                                                                                 | The path for the OpenShift Route.                                                                                                                                                                                                                                    |
| `route.tls.enabled`                        | `bool` | `true`                                                                                                                               | Enables or disables TLS for the OpenShift Route, providing secure communication.                                                                                                                                                                                          |
| `route.tls.insecureEdgeTerminationPolicy`    | `string` | `"Redirect"`                                                                                                                         | The policy for handling insecure (HTTP) requests when TLS termination is at the edge (Route).                                                                                                                                                                         |
| `route.tls.termination`                    | `string` | `"edge"`                                                                                                                             | Specifies that TLS termination occurs at the OpenShift Route edge.                                                                                                                                                                                                      |
| `service.port`                             | `int`  | `5001`                                                                                                                               | The port on which the Kubernetes Service will be exposed internally within the cluster.                                                                                                                                                                                  |
| `service.type`                             | `string` | `"ClusterIP"`                                                                                                                        | The type of Kubernetes Service. `ClusterIP` makes the service only reachable from within the cluster.                                                                                                                                                                 |
| `serviceAccount.annotations`               | `object` | `{}`                                                                                                                                 | Annotations for the Kubernetes ServiceAccount.                                                                                                                                                                                                                       |
| `serviceAccount.automount`                 | `bool` | `true`                                                                                                                               | Indicates whether the ServiceAccount token should be automatically mounted into the Pods.                                                                                                                                                                            |
| `serviceAccount.create`                    | `bool` | `false`                                                                                                                              | Determines whether a new Kubernetes ServiceAccount should be created.                                                                                                                                                                                                 |
| `serviceAccount.name`                      | `string` | `""`                                                                                                                                 | The name of an existing Kubernetes ServiceAccount to use. If `create` is true and this is empty, a default name will be generated.                                                                                                                                     |
| `startupProbe.failureThreshold`            | `int`  | `30`                                                                                                                                 | The number of consecutive failures of the startup probe before Kubernetes considers the container failed to start.                                                                                                                                                  |
| `startupProbe.httpGet.path`                | `string` | `"/v1/health"`                                                                                                                      | The HTTP endpoint path for the startup probe, used to determine if the application has started successfully.                                                                                                                                                           |
| `startupProbe.httpGet.port`                | `int`  | `5001`                                                                                                                               | The port for the HTTP startup probe.                                                                                                                                                                                                                                 |
| `startupProbe.initialDelaySeconds`         | `int`  | `40`                                                                                                                                 | The number of seconds to wait after the container has started before the startup probe is first initiated.                                                                                                                                                            |
| `startupProbe.periodSeconds`               | `int`  | `10`                                                                                                                                 | The interval (in seconds) at which the startup probe will be executed.                                                                                                                                                                                               |
| `volumeMounts`                             | `list`   | `[]`                                                                                                                                 | A list of volume mounts that define how volumes should be mounted into the container's filesystem.                                                                                                                                                                   |
| `volumes`                                  | `list`   | `[]`                                                                                                                                 | A list of volume definitions that provide storage for the Pod.                                                                                                                                                                                                          |
