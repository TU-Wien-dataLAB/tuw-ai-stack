#!/usr/bin/env -S uv run --with pyyaml --script

import subprocess
import sys
from pathlib import Path
import yaml


def get_chart_resources(chart_path):
    """Parse helm template output for resources"""
    result = subprocess.run(
        ["helm", "template", "test", chart_path],
        capture_output=True,
        text=True,
        check=True,
    )

    resources = {
        "external_secrets": [],
        "cluster_issuers": [],
        "ingresses": [],
        "pvcs": [],
        "secrets": [],
    }

    external_secret_keys = {}

    for doc_text in result.stdout.split("\n---\n"):
        if not doc_text.strip():
            continue

        try:
            doc = yaml.safe_load(doc_text)
            if not doc or not isinstance(doc, dict):
                continue

            kind = doc.get("kind", "")
            name = doc.get("metadata", {}).get("name") or ""
            name = name.strip() if isinstance(name, str) else ""
            name = name or "<unnamed>"

            if kind == "ExternalSecret":
                resources["external_secrets"].append(name)
                # Extract vault keys
                spec = doc.get("spec", {})
                store = spec.get("secretStoreRef", {}).get("name", "unknown")
                keys = set()
                for item in spec.get("data", []):
                    key = item.get("remoteRef", {}).get("key")
                    if key:
                        keys.add(key)
                external_secret_keys[name] = {"store": store, "keys": list(keys)}

            elif kind == "ClusterIssuer":
                resources["cluster_issuers"].append(name)

            elif kind == "Ingress":
                spec = doc.get("spec", {})
                hosts = [r.get("host", "") for r in spec.get("rules", [])]
                hosts = [h for h in hosts if h]
                if hosts:
                    resources["ingresses"].append(f"{name} → {', '.join(hosts)}")
                else:
                    resources["ingresses"].append(name)

            elif kind == "PersistentVolumeClaim":
                spec = doc.get("spec", {})
                storage = (
                    spec.get("resources", {}).get("requests", {}).get("storage", "?")
                )
                resources["pvcs"].append(f"{name} ({storage})")

            elif kind == "Secret":
                resources["secrets"].append(name)

        except yaml.YAMLError:
            pass

    return resources, external_secret_keys


def main():
    charts_dir = Path(__file__).parent.parent / "charts"
    charts = sorted(
        [d.name for d in charts_dir.iterdir() if (d / "Chart.yaml").exists()]
    )

    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage: list-chart-resources.py [CHART_NAME]")
            print(f"\nAvailable charts: {', '.join(charts)}")
            sys.exit(0)

        chart_name = sys.argv[1]
        if chart_name not in charts:
            print(f"Error: Chart '{chart_name}' not found")
            print(f"Available charts: {', '.join(charts)}")
            sys.exit(1)
        charts = [chart_name]

    print("=" * 60)
    print("Helm Chart Resources")
    print("=" * 60)
    print()

    for chart in charts:
        try:
            resources, ext_secret_keys = get_chart_resources(charts_dir / chart)

            print(f"### {chart}")
            print()

            has_resources = False

            if resources["external_secrets"]:
                has_resources = True
                print("ExternalSecrets (needs vault configuration):")
                for name in resources["external_secrets"]:
                    details = ext_secret_keys.get(name, {})
                    store = details.get("store", "")
                    keys = details.get("keys", [])
                    info = f"  • {name}"
                    if store:
                        info += f" [{store}]"
                    if keys:
                        info += f" → {', '.join(keys)}"
                    print(info)
                print()

            if resources["cluster_issuers"]:
                has_resources = True
                print("ClusterIssuers:")
                for item in resources["cluster_issuers"]:
                    print(f"  • {item}")
                print()

            if resources["ingresses"]:
                has_resources = True
                print("Ingresses:")
                for item in resources["ingresses"]:
                    print(f"  • {item}")
                print()

            if resources["pvcs"]:
                has_resources = True
                print("PersistentVolumeClaims:")
                for item in resources["pvcs"]:
                    print(f"  • {item}")
                print()

            if resources["secrets"]:
                has_resources = True
                print(f"Secrets: {len(resources['secrets'])}")
                print()

            if not has_resources:
                print("  (no special resources)")
                print()

        except subprocess.CalledProcessError:
            print(f"### {chart}")
            print()
            print("  Error: Failed to template chart")
            print()

        print()


if __name__ == "__main__":
    main()
