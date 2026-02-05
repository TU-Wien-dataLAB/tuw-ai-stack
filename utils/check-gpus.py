#!/usr/bin/env -S uv run --with kubernetes

from kubernetes import client, config


def main():
    config.load_kube_config()
    v1 = client.CoreV1Api()

    # Get GPU nodes
    nodes = v1.list_node()
    gpu_nodes = {}
    total_gpus = 0
    total_allocatable = 0

    for node in nodes.items:
        capacity = node.status.capacity or {}
        if any("gpu" in k.lower() or "nvidia" in k.lower() for k in capacity):
            gpu_count = int(next(v for k, v in capacity.items() if "gpu" in k.lower()))
            allocatable = node.status.allocatable or {}
            allocatable_count = int(
                next(v for k, v in allocatable.items() if "gpu" in k.lower())
            )

            # Get GPU type from node labels
            gpu_type = "Unknown"
            if node.metadata.labels:
                gpu_type = node.metadata.labels.get("nvidia.com/gpu.product", "Unknown")
                if gpu_type == "Unknown":
                    # Try common label patterns
                    for label_key, label_value in node.metadata.labels.items():
                        if (
                            "gpu" in label_key.lower()
                            or "accelerator" in label_key.lower()
                        ):
                            gpu_type = label_value
                            break

            gpu_nodes[node.metadata.name] = {
                "type": gpu_type,
                "capacity": gpu_count,
                "allocatable": allocatable_count,
            }
            total_gpus += gpu_count
            total_allocatable += allocatable_count

    if not gpu_nodes:
        print("❌ No GPU nodes found")
        return

    # Get GPU usage by pods with node allocation
    pods = v1.list_pod_for_all_namespaces()
    node_usage = {name: 0 for name in gpu_nodes}
    used_gpus = 0

    for pod in pods.items:
        if pod.status.phase not in ["Running", "Pending"]:
            continue

        # Get the node this pod is scheduled on
        node_name = pod.spec.node_name
        if not node_name or node_name not in gpu_nodes:
            continue

        for container in pod.spec.containers:
            if container.resources and container.resources.requests:
                for resource, amount in container.resources.requests.items():
                    if "gpu" in resource.lower() or "nvidia" in resource.lower():
                        gpu_amount = int(amount)
                        node_usage[node_name] += gpu_amount
                        used_gpus += gpu_amount
                        break

    # Calculate free GPUs by type
    free_by_type = {}
    total_free = 0

    for name, info in gpu_nodes.items():
        free_count = info["allocatable"] - node_usage[name]
        if free_count > 0:
            gpu_type = info["type"]
            free_by_type[gpu_type] = free_by_type.get(gpu_type, 0) + free_count
            total_free += free_count

    print(f"🖥️  GPU Status:")
    for name, info in gpu_nodes.items():
        free = info["allocatable"] - node_usage[name]
        print(f"  {name}: {free}/{info['allocatable']} {info['type']}")

    print(f"\n📊 Summary:")
    print(f"  Total: {total_allocatable} GPUs")
    print(f"  Used:  {used_gpus} GPUs")
    print(f"  Free:  {total_free} GPUs")

    if free_by_type:
        print(f"\n🔋 Free GPUs by Type:")
        for gpu_type, count in free_by_type.items():
            print(f"  {gpu_type}: {count}")

    print(f"\n📈 Usage: {(used_gpus / total_allocatable * 100):.1f}%")


if __name__ == "__main__":
    main()
