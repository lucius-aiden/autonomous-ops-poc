#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
helm uninstall otel-demo --namespace ops-sandbox || true
kubectl delete namespace ops-sandbox --ignore-not-found
"$(dirname "$0")/sandbox-up.sh"

