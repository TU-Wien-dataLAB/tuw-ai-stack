#!/usr/bin/env -S uv run --with kubernetes

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Optional

from kubernetes import client, config


CUSTOM_ERRORS_ANNOTATION = "nginx.ingress.kubernetes.io/custom-http-errors"
DEFAULT_BACKEND_ANNOTATION = "nginx.ingress.kubernetes.io/default-backend"

# This should match the serviceName in values.yaml
MAINTENANCE_BACKEND_NAME = "maintenance-backend"


def deploy_maintenance_chart(
    namespace: str,
    until: Optional[str] = None,
) -> bool:
    """Deploy the maintenance-page Helm chart."""
    until_date = until or (datetime.now() + timedelta(hours=2)).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    # Build helm command
    cmd = [
        "helm",
        "upgrade",
        "--install",
        "maintenance-page",  # release name
        "charts/maintenance-page",  # chart path
        "--namespace",
        namespace,
        "--set",
        f"maintenance.until={until_date}",
    ]

    print(f"Deploying maintenance-page chart to namespace '{namespace}'...")
    print(f"   Maintenance until: {until_date}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Helm deployment failed:")
        print(f"   {e.stderr}")
        return False


def uninstall_maintenance_chart(namespace: str) -> bool:
    """Uninstall the maintenance-page Helm chart."""
    cmd = [
        "helm",
        "uninstall",
        "maintenance-page",
        "--namespace",
        namespace,
    ]

    print(f"Removing maintenance-page chart from namespace '{namespace}'...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Helm uninstall failed:")
        print(f"   {e.stderr}")
        return False


def is_in_maintenance_mode(annotations: dict) -> bool:
    return (
        CUSTOM_ERRORS_ANNOTATION in annotations
        and DEFAULT_BACKEND_ANNOTATION in annotations
        and annotations.get(DEFAULT_BACKEND_ANNOTATION) == MAINTENANCE_BACKEND_NAME
    )


def enable_maintenance(
    ingress_name: str,
    namespace: str,
    until: Optional[str] = None,
) -> bool:
    config.load_kube_config()
    networking_v1 = client.NetworkingV1Api()

    try:
        ingress = networking_v1.read_namespaced_ingress(ingress_name, namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Ingress '{ingress_name}' not found in namespace '{namespace}'")
            return False
        raise

    annotations = ingress.metadata.annotations or {}

    if is_in_maintenance_mode(annotations):
        print(f"'{ingress_name}' is already in maintenance mode, updating chart...")
        return deploy_maintenance_chart(namespace, until)

    # Deploy the Helm chart first
    if not deploy_maintenance_chart(namespace, until):
        return False

    # Add annotations to intercept 503 and route to maintenance backend
    annotations[CUSTOM_ERRORS_ANNOTATION] = "503"
    annotations[DEFAULT_BACKEND_ANNOTATION] = MAINTENANCE_BACKEND_NAME
    ingress.metadata.annotations = annotations

    networking_v1.replace_namespaced_ingress(ingress_name, namespace, ingress)

    until_display = until or (datetime.now() + timedelta(hours=2)).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    print(f"🔒 Maintenance mode ENABLED for '{ingress_name}'")
    print(f"   Until: {until_display}")
    print(f"   Next step: scale down your backend to trigger 503s")
    return True


def disable_maintenance(
    ingress_name: str, namespace: str, keep_chart: bool = False
) -> bool:
    config.load_kube_config()
    networking_v1 = client.NetworkingV1Api()

    try:
        ingress = networking_v1.read_namespaced_ingress(ingress_name, namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Ingress '{ingress_name}' not found in namespace '{namespace}'")
            return False
        raise

    annotations = ingress.metadata.annotations or {}

    if not is_in_maintenance_mode(annotations):
        print(f"'{ingress_name}' is not in maintenance mode")
        return True

    # Remove maintenance annotations
    annotations.pop(CUSTOM_ERRORS_ANNOTATION, None)
    annotations.pop(DEFAULT_BACKEND_ANNOTATION, None)
    ingress.metadata.annotations = annotations

    networking_v1.replace_namespaced_ingress(ingress_name, namespace, ingress)

    # Optionally remove the Helm chart
    if not keep_chart:
        uninstall_maintenance_chart(namespace)

    print(f"🔓 Maintenance mode DISABLED for '{ingress_name}'")
    if keep_chart:
        print(
            f"   Note: maintenance-page chart still deployed in namespace '{namespace}'"
        )
        print(f"   To remove: helm uninstall maintenance-page -n {namespace}")
    return True


def check_status(ingress_name: str, namespace: str) -> bool:
    config.load_kube_config()
    networking_v1 = client.NetworkingV1Api()

    try:
        ingress = networking_v1.read_namespaced_ingress(ingress_name, namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Ingress '{ingress_name}' not found in namespace '{namespace}'")
            return False
        raise

    annotations = ingress.metadata.annotations or {}

    # Check if maintenance chart is deployed
    try:
        result = subprocess.run(
            ["helm", "status", "maintenance-page", "-n", namespace],
            capture_output=True,
            text=True,
            check=True,
        )
        chart_deployed = True
    except subprocess.CalledProcessError:
        chart_deployed = False

    if is_in_maintenance_mode(annotations):
        print(f"'{ingress_name}' is in MAINTENANCE mode")
        print(f"   custom-http-errors: {annotations.get(CUSTOM_ERRORS_ANNOTATION)}")
        print(f"   default-backend: {annotations.get(DEFAULT_BACKEND_ANNOTATION)}")
    else:
        print(f"'{ingress_name}' is ACTIVE (not in maintenance)")

    if chart_deployed:
        print(f"   Chart: maintenance-page is deployed")
    else:
        print(f"   Chart: maintenance-page is not deployed")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Toggle maintenance mode for a Kubernetes ingress.\n\n"
        "Deploys a maintenance-page Helm chart and sets per-ingress annotations\n"
        "to intercept 503 errors with a custom maintenance page.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "ingress",
        help="Name of the ingress",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        default="default",
        help="Namespace of the ingress (default: default)",
    )
    parser.add_argument(
        "-u",
        "--until",
        metavar="DATE",
        help="Maintenance end date/time (e.g. '2026-02-15 14:00 UTC')",
    )
    parser.add_argument(
        "-d",
        "--disable",
        action="store_true",
        help="Disable maintenance mode (remove annotations)",
    )
    parser.add_argument(
        "--keep-chart",
        action="store_true",
        help="Keep the Helm chart deployed when disabling (default: uninstall)",
    )
    parser.add_argument(
        "-s",
        "--status",
        action="store_true",
        help="Check maintenance status",
    )

    args = parser.parse_args()

    if args.status:
        success = check_status(args.ingress, args.namespace)
    elif args.disable:
        success = disable_maintenance(
            args.ingress,
            args.namespace,
            keep_chart=args.keep_chart,
        )
    else:
        success = enable_maintenance(args.ingress, args.namespace, until=args.until)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
