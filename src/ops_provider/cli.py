import argparse
import json

from .kubernetes import KubernetesProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled ops-sandbox Kubernetes tools")
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("health", "services"):
        sub.add_parser(name)
    service = sub.add_parser("service")
    service.add_argument("name")
    logs = sub.add_parser("logs")
    logs.add_argument("name")
    logs.add_argument("--tail", type=int, default=100)
    restart = sub.add_parser("restart")
    restart.add_argument("name")
    scale = sub.add_parser("scale")
    scale.add_argument("name")
    scale.add_argument("replicas", type=int)
    args = parser.parse_args()
    provider = KubernetesProvider()
    if args.operation == "health": result = provider.get_cluster_health()
    elif args.operation == "services": result = provider.list_services()
    elif args.operation == "service": result = provider.get_service_health(args.name)
    elif args.operation == "logs": result = provider.get_logs(args.name, args.tail)
    elif args.operation == "restart": result = provider.restart_service(args.name).__dict__
    else: result = provider.scale_service(args.name, args.replicas).__dict__
    print(result if isinstance(result, str) else json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

