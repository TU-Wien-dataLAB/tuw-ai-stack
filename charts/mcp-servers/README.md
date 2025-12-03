# MCP Servers Helm Chart

A Helm chart for deploying MCP (Model Context Protocol) servers using standard Node.js or Python runtime images with `npx` or `uvx`.

## Features

- **Smart Image Selection**: Automatically selects Node.js or Python base images based on command
- **Multiple Servers**: Deploy any number of MCP servers from a single chart
- **Flexible Commands**: Support for any command structure with full argument support
- **Environment Variables**: Complete support for both direct values and `valueFrom` (secrets, configMaps, fieldRefs)
- **Init Containers Support**: Run setup tasks before main container with shared environment
- **Service Integration**: Optional services for each server
- **Configuration Management**: Support for ConfigMaps and Secrets
- **Standard Kubernetes Features**: Full support for resources, node selectors, tolerations, affinity, volumes

## Quick Start

### Node.js MCP Server (using npx)

```bash
helm install my-mcp-servers . \
  --set mcpServers[0].enabled=true \
  --set mcpServers[0].name=filesystem \
  --set mcpServers[0].command[0]=npx \
  --set mcpServers[0].command[1]="@modelcontextprotocol/server-filesystem" \
  --set mcpServers[0].command[2]="/data" \
  --set mcpServers[0].service.type=ClusterIP \
  --set mcpServers[0].service.port=80
```

### Python MCP Server (using uvx)

```bash
helm install my-mcp-servers . \
  --set mcpServers[0].enabled=true \
  --set mcpServers[0].name=git \
  --set mcpServers[0].command[0]=uvx \
  --set mcpServers[0].command[1]="mcp-server-git" \
  --set mcpServers[0].command[2]="--directory" \
  --set mcpServers[0].command[3]="/workspace" \
  --set mcpServers[0].service.type=ClusterIP
```

### Server with Init Containers

```bash
helm install my-mcp-servers . \
  --set mcpServers[0].enabled=true \
  --set mcpServers[0].name=git \
  --set mcpServers[0].command[0]=uvx \
  --set mcpServers[0].command[1]="mcp-server-git" \
  --set mcpServers[0].command[2]="--directory" \
  --set mcpServers[0].command[3]="/workspace" \
  --set mcpServers[0].initContainers[0].name=setup-permissions \
  --set mcpServers[0].initContainers[0].command[0]=sh \
  --set mcpServers[0].initContainers[0].command[1]="-c" \
  --set mcpServers[0].initContainers[0].command[2]="mkdir -p /workspace && chmod 755 /workspace" \
  --set mcpServers[0].initContainers[1].name=wait-for-service \
  --set mcpServers[0].initContainers[1].image=busybox:1.35 \
  --set mcpServers[0].initContainers[1].command[0]=sh \
  --set mcpServers[0].initContainers[1].command[1]="-c" \
  --set mcpServers[0].initContainers[1].command[2]="echo 'Waiting...' && sleep 2" \
  --set mcpServers[0].service.type=ClusterIP
```

### Multiple Servers

```bash
helm install my-mcp-servers . \
  --set mcpServers[0].enabled=true \
  --set mcpServers[0].name=filesystem \
  --set mcpServers[0].command[0]=npx \
  --set mcpServers[0].command[1]="@modelcontextprotocol/server-filesystem" \
  --set mcpServers[0].command[2]="/home/user" \
  --set mcpServers[1].enabled=true \
  --set mcpServers[1].name=git \
  --set mcpServers[1].command[0]=uvx \
  --set mcpServers[1].command[1]="mcp-server-git" \
  --set mcpServers[1].service.type=ClusterIP
```

### Init Containers

The chart supports init containers for setup tasks that need to run before the main MCP server:

```yaml
initContainers:
  - name: setup-permissions
    command: ["sh", "-c", "chmod 755 /data && chown app:app /data"]
  - name: wait-for-service
    image: busybox:1.35
    command: ["sh", "-c", "until nc -z database 5432; do sleep 1; done"]
```

**Key Features:**
- **Environment Inheritance**: Init containers automatically inherit all environment variables from the main server container, including `valueFrom` configurations
- **Volume Sharing**: Init containers have access to all volumes and volume mounts defined for the main container
- **Flexible Imaging**: Each init container can specify its own image, or default to the main container's image
- **Simple Configuration**: Only need to specify `name` and `command` - environment and volumes are shared automatically

**Use Cases:**
- Database migration scripts
- File permissions setup
- Waiting for external services
- Configuration validation
- Resource preparation

## Configuration

### Image Configuration

The chart uses a unified image that supports both Python 3.12 and Node.js 25, making it suitable for both `npx` and `uvx` commands:

- Default image: `nikolaik/python-nodejs:python3.12-nodejs25-slim`
- Supports both Node.js (`npx`) and Python (`uvx`) commands in the same image
- Simplified deployment with a single base image containing both runtimes

You can override the image per server:

```yaml
mcpServers:
  - name: custom-server
    image:
      repository: python
      tag: "3.12-slim"
      pullPolicy: Always
    command: ["python", "-m", "my_custom_mcp_server"]
```

### Environment Variables

Support for both direct values and `valueFrom`:

```yaml
env:
  - name: DIRECT_VALUE
    value: "some-value"
  - name: SECRET_VALUE
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: api-key
  - name: CONFIG_VALUE
    valueFrom:
      configMapKeyRef:
        name: my-config
        key: config-key
```

### Configuration Files

For servers that need configuration files:

```yaml
configData:
  config.yaml: |
    setting1: value1
    setting2: value2

secretData:
  api-key: "secret-value"
  .env: |
    SECRET_VAR=secret_value
```

### Storage

Support for volumes and volumeMounts:

```yaml
volumes:
  - name: workspace
    persistentVolumeClaim:
      claimName: git-workspace
  - name: config
    configMap:
      name: server-config

volumeMounts:
  - name: workspace
    mountPath: /workspace
  - name: config
    mountPath: /etc/config
```

### Init Containers Example

Complete example with setup tasks and environment access:

```yaml
mcpServers:
  - name: git-server
    enabled: true
    replicas: 1
    command:
      - "uvx"
      - "mcp-server-git"
      - "--directory"
      - "/workspace"
    
    # Init containers with shared environment
    initContainers:
      - name: setup-workspace
        command: 
          - "sh"
          - "-c"
          - |
            echo "Setting up workspace directory..."
            mkdir -p /workspace/.git
            chmod 755 /workspace
            echo "Workspace ready"
      
      - name: wait-for-git-ssh
        image: busybox:1.35
        command:
          - "sh"
          - "-c"
          - |
            echo "Waiting for Git SSH service..."
            until nc -z git-ssh 22; do
              echo "Waiting for git-ssh..."
              sleep 2
            done
            echo "Git SSH service is ready"
    
    # Environment that init containers inherit
    env:
      - name: GIT_SSH_COMMAND
        value: "ssh -i /app/ssh/id_rsa"
      - name: WORKSPACE_DIR
        value: "/workspace"
      - name: GIT_SSH_KEY
        valueFrom:
          secretKeyRef:
            name: git-ssh-key
            key: id_rsa
    
    # Volumes that both init containers and main container can access
    volumeMounts:
      - name: workspace
        mountPath: /workspace
      - name: ssh-key
        mountPath: /app/ssh
        readOnly: true
    
    volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: git-workspace
      - name: ssh-key
        secret:
          secretName: git-ssh-key
    
    resources:
      limits:
        memory: "512Mi"
        cpu: "250m"
      requests:
        memory: "256Mi"
        cpu: "100m"
    
    service:
      type: ClusterIP
      port: 80
      targetPort: 3000
```

### Resources and Scheduling

```yaml
resources:
  limits:
    memory: "1Gi"
    cpu: "500m"
  requests:
    memory: "512Mi"
    cpu: "250m"

nodeSelector:
  kubernetes.io/os: linux

tolerations:
- key: "key"
  operator: "Equal"
  value: "value"
  effect: "NoSchedule"

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - my-mcp-server
        topologyKey: kubernetes.io/hostname
```

## Values Reference

### Global Configuration

- `global.imagePullSecrets` - Global image pull secrets

### Default Image

- `defaultImage.repository` - Default unified image repository (`nikolaik/python-nodejs`)
- `defaultImage.tag` - Default image tag (`python3.12-nodejs25-slim`)
- `defaultImage.pullPolicy` - Default pull policy (`IfNotPresent`)

### Server Configuration

Each server in `mcpServers` can configure:

- `enabled` - Whether to deploy this server (required)
- `name` - Server name (required)
- `command` - Command and arguments to run the server (required)
- `replicas` - Number of replicas (default `1`)
- `proxy` - Proxy configuration (optional)
  - `enabled` - Enable transport bridging for stdio servers (default `false`)
- `image` - Custom image configuration (optional, auto-selected for proxy mode)
- `env` - Environment variables array (optional)
- `ports` - Container ports (optional, auto-configured for proxy mode)
- `volumes` - Pod volumes (optional)
- `volumeMounts` - Container volume mounts (optional)
- `service` - Service configuration (optional)
  - `targetPort` - Port number for proxy mode (default `3000`)
- `configData` - ConfigMap data (optional)
- `secretData` - Secret data (optional)
- `resources` - Resource limits/requests (optional)
- `nodeSelector` - Node selector (optional)
- `tolerations` - Tolerations (optional)
- `affinity` - Affinity rules (optional)
- `initContainers` - List of init containers (optional)
  - `name` - Container name (required)
  - `image` - Container image (optional, defaults to main container image)
  - `command` - Command array to run (required)
  - *All environment variables and volume mounts are inherited automatically*

**Proxy Mode Behavior**: When `proxy.enabled: true`, the chart automatically configures the FastMCP proxy, volumes, image, and command generation based on the `command` field and server settings.

## Transport Bridging with Proxy Mode

Some MCP servers only support stdio transport (e.g., `@modelcontextprotocol/server-time`). To expose these servers via HTTP in Kubernetes, this chart supports transport bridging using FastMCP's proxy capabilities.

### How It Works

The proxy mode runs a FastMCP proxy server that:
1. Accepts streamableHttp requests from clients
2. Spawns the stdio-based MCP server as a subprocess
3. Forwards requests/responses between transports using FastMCP's `ProxyClient`
4. Provides session isolation for concurrent requests

### Configuration

**Simplified Proxy Configuration** (Recommended)

When you set `proxy.enabled: true`, the chart automatically generates all the necessary proxy configuration:

```yaml
mcpServers:
  - name: time-server
    enabled: true
    proxy:
      enabled: true
    # The backend command for the actual MCP server
    command:
      - "uvx"
      - "mcp-server-time"
      - "--local-timezone=Europe/Vienna"
    # Optional: specify server name and port
    service:
      targetPort: 3000  # Default: 3000
    resources:
      limits:
        memory: "512Mi"
        cpu: "250m"
      requests:
        memory: "256Mi"
        cpu: "100m"
```

**That's it!** The chart automatically:
- **Selects the appropriate image** (`nikolaik/python-nodejs:python3.12-nodejs25-slim`)
- **Generates the full proxy command** with FastMCP
- **Adds required volumes and volumeMounts** for the proxy script
- **Uses the server name** (capitalized) as the proxy server name
- **Uses the service targetPort** (default: 3000) for the proxy port

**Backend Command Format**

The `command` field should contain the actual command to run your MCP server:

**Examples:**
- `["uvx", "mcp-server-time", "--local-timezone=Europe/Vienna"]`
- `["uvx", "mcp-server-git", "--directory", "/workspace"]`
- `["python", "-m", "my_mcp_server", "--config", "/etc/config.yaml"]`
- `["npx", "@modelcontextprotocol/server-filesystem", "/data"]`

### Proxy Configuration Details

The proxy automatically configures these arguments:
- `--backend-command`: The command array from your `command` field (auto-joined)
- `--server-name`: Your server name capitalized (e.g., `time-server` → `TimeServer`)
- `--port`: Your service `targetPort` (default: 3000)
- `--host`: Always `0.0.0.0` (bind to all interfaces)

### Key Features

- **Session Isolation**: Each request gets an isolated backend session using `ProxyClient`
- **Transport**: Always uses streamableHttp transport (not SSE)
- **MCP Feature Support**: Automatic forwarding of sampling, logging, progress, and elicitation
- **Production Ready**: Supports resource limits, replicas, and all standard Kubernetes features

### Performance Considerations

Proxy servers add some latency compared to direct connections:
- Typical overhead: 50-200ms per request
- Session creation adds initial startup time
- For low-latency requirements, consider using servers that natively support HTTP transport

### Dependencies

Proxy mode automatically handles all dependencies:
- **FastMCP**: Automatically installed via `uvx --with fastmcp --from fastmcp`
- **Python 3.12**: Built into the `nikolaik/python-nodejs:python3.12-nodejs25-slim` image
- **Node.js 25**: Available in the same image for `npx` commands

No additional setup required - the chart handles everything.

### Direct Command Line Usage

You can also run the proxy directly without Kubernetes:

```bash
# Run proxy locally with FastMCP pip installation
pip install fastmcp
python proxy.py --backend-command "uvx mcp-server-time --local-timezone=Europe/Vienna" --server-name LocalTest --port 8080

# Or using uvx (recommended)
uvx --with fastmcp --from fastmcp python proxy.py --backend-command "uvx mcp-server-time --local-timezone=Europe/Vienna" --server-name LocalTest --port 8080
```

The proxy will start on `http://localhost:8080` and bridge all requests to the backend MCP server.

## Examples

See `values.yaml` for comprehensive examples of different server configurations, including:
- Direct HTTP/streamableHttp servers
- Stdio servers with transport bridging (proxy mode)
- Custom images and configurations

## Generated Resources

For each enabled server, the chart generates:

- 1 Deployment with the MCP server container (+ init containers if configured)
- 1 Service (if service configuration is provided)
- 1 ConfigMap (if configData is provided)
- 1 Secret (if secretData is provided)

Additionally, if any server has proxy mode enabled:
- 1 global ConfigMap (`mcp-proxy-script`) containing the proxy.py script

All resources are labeled with the release name, server name, and appropriate selectors.