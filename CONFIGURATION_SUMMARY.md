# Llama Stack Configuration Summary

## What Changed

The Llama Stack configuration has been completely refactored to use a **ConfigMap-based approach** instead of environment variables and embedded Python package files.

## Key Changes

### 1. **Dockerfile** (`utils/llama-stack-distribution/Dockerfile`)
- Pinned llama-stack to version `0.3.3` for stability
- No longer relies on copying files to Python site-packages location

### 2. **ConfigMap Template** (`charts/llama-stack/templates/configmap.yaml`)
- New file that generates run.yaml from Helm values
- Mounted at `/etc/llama-stack/run.yaml`

### 3. **Values Configuration** (`charts/llama-stack/values.yaml`)
- Added complete `runConfig` section containing the full run.yaml
- Removed `vectorStore` shortcut section (all config now in runConfig)
- All configuration uses static defaults (no environment variable interpolation)

### 4. **Deployment** (`charts/llama-stack/templates/deployment.yaml`)
- Added `RUN_CONFIG_PATH=/etc/llama-stack/run.yaml` environment variable
- Removed all `VECTOR_STORE_*` environment variables
- Added ConfigMap volume mount at `/etc/llama-stack`

### 5. **Base run.yaml** (`utils/llama-stack-distribution/tuw-ai/run.yaml`)
- Changed from environment variable defaults to static defaults
- Uses `sentence-transformers/nomic-ai/nomic-embed-text-v1.5` with 768 dimensions
- Added `allowed_models: []` to vLLM provider config to prevent auto-registration

## Architecture

```
Helm Values (values.yaml)
    └── runConfig (complete run.yaml structure)
            │
            ▼ helm template
        ConfigMap
            └── run.yaml
                    │
                    ▼ mounted as volume
                Container
                    └── RUN_CONFIG_PATH=/etc/llama-stack/run.yaml
```

## Benefits

✅ **No Python version dependency** - Not tied to `/usr/local/lib/python3.12/site-packages/`
✅ **Single source of truth** - All configuration in `runConfig` section
✅ **Declarative** - Full YAML structure in Helm values
✅ **No image rebuilds** - Configuration changes via `helm upgrade`
✅ **Version stability** - llama-stack pinned to 0.3.3
✅ **Clear separation** - Environment variables only for runtime (VLLM_URL, etc), configuration in ConfigMap

## Default Configuration

- **Vector Store**: faiss (in-memory)
- **Embedding Model**: sentence-transformers/nomic-ai/nomic-embed-text-v1.5
- **Embedding Dimension**: 768

## Customization Example

To use vLLM embeddings with Milvus:

```yaml
# custom-values.yaml
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

Deploy:
```bash
helm upgrade -i llama-stack charts/llama-stack -f custom-values.yaml
```

## Important: vLLM Model Auto-Registration

### Problem
vLLM automatically discovers and registers all models at its endpoint. When embedding models are served via vLLM:
1. vLLM auto-registers them as **text completion models** (incorrect)
2. When you try to register them correctly as **embedding models**, you get:
   ```
   ValueError: Object of type 'model' and identifier 'vllm/intfloat/e5-mistral-7b-instruct' 
   already exists. Unregister it first if you want to replace it.
   ```

### Solution
Set `allowed_models: []` in the vLLM provider configuration:

```yaml
runConfig:
  providers:
    inference:
      - provider_id: ${env.VLLM_URL:+vllm}
        provider_type: remote::vllm
        config:
          allowed_models: []  # Prevents auto-registration
```

This prevents vLLM from auto-registering models, allowing you to manually register them with the correct `model_type: embedding` in `registered_resources.models`.

## Migration Notes

- **Old approach**: Set environment variables like `VECTOR_STORE_DEFAULT_PROVIDER`
- **New approach**: Modify `runConfig.vector_stores.default_provider_id` in values.yaml
- **No breaking changes**: Existing deployments will continue to work with defaults
