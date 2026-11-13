#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PATH="$HOME/.local/bin:$PATH"

command -v docker >/dev/null || { echo "Docker is required" >&2; exit 1; }
command -v kind >/dev/null || { echo "kind is required; see README" >&2; exit 1; }
command -v kubectl >/dev/null || { echo "kubectl is required; see README" >&2; exit 1; }
command -v helm >/dev/null || { echo "Helm is required; see README" >&2; exit 1; }

if ! kind get clusters | grep -qx ops-poc; then
  kind create cluster --config "$ROOT/kind-config.yaml" --wait 120s
fi
kubectl create namespace ops-sandbox --dry-run=client -o yaml | kubectl apply -f - >/dev/null
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install otel-demo open-telemetry/opentelemetry-demo \
  --namespace ops-sandbox --create-namespace \
  --set default.replicas=1 \
  --wait --timeout 15m
echo "Sandbox is up. Run: make sandbox-status"

