#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
kubectl cluster-info
kubectl -n ops-sandbox get deployments,pods,services -o wide

