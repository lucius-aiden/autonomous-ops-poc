# Autonomous Ops POC

Phase 1 is a zero-cost, local proof of concept for an autonomous first-line IT/security operations agent governed by MetaMynd. It deliberately does **not** contain an LLM agent, OpenRig, MetaMynd integration, frontend, customer connectors, or production-security claims.

## What Phase 1 proves

- A real single-node [kind](https://kind.sigs.k8s.io/) Kubernetes cluster can be recreated locally.
- The real OpenTelemetry Demo runs as Kubernetes workloads in `ops-sandbox`.
- Python operations tools inspect real cluster state and logs.
- The same constrained tool layer performs real deployment restart and scaling operations.
- A reversible scale-to-zero failure is observed and remediated through the tool layer.

The demo, Kubernetes API responses, pod transitions, and logs are real. Unit tests use controlled runner fixtures; the live smoke test never mocks Kubernetes.

## Prerequisites

- Linux/macOS with Docker running, 6+ CPUs and about 8–10 GiB available RAM recommended.
- Python 3.11+.
- `kind`, `kubectl`, and Helm 3/4 on `PATH`.
- `make`.

On this development machine the binaries are in `~/.local/bin`: kind v0.31.0, kubectl v1.34.1, Helm v4.0.0, Docker 29.1.3, Python 3.12.3.

## Start, inspect, test, reset, stop

```bash
make sandbox-up       # create kind cluster and install the OpenTelemetry Demo
make sandbox-status   # show nodes, deployments, pods, and services
make sandbox-test     # real inspect/restart/scale/failure/recovery experiment
make sandbox-reset    # uninstall and recreate the demo namespace
make sandbox-down     # delete the kind cluster
make unit-test        # unit tests for the operations adapter
```

The first `sandbox-up` downloads container images and may take several minutes. `sandbox-test` uses the `frontend` deployment and restores its original replica count even after each normal experiment step. If interrupted during the controlled failure, run `make sandbox-reset`.

## Architecture

```text
future agent / MetaMynd boundary (not implemented)
                 |
          OperationsProvider
                 |
         KubernetesProvider
                 |
       fixed, validated kubectl calls
                 |
     kind -> ops-sandbox -> OTel Demo
```

`KubernetesProvider` is the only operations boundary. Resource names are validated, all operations are namespace-scoped, and arbitrary shell execution is not exposed. `restart_service` and `scale_service` are the consequential methods where MetaMynd authorization must be inserted in Phase 2; no fake policy layer is present.

## Repository layout

- `src/ops_provider/` — provider protocol, structured result model, constrained Kubernetes implementation, CLI.
- `scripts/` — reproducible kind/Helm lifecycle and live experiment.
- `tests/` — unit tests; no live-cluster behavior is mocked into the experiment.
- `docs/ARCHITECTURE.md` — trust and execution boundary.
- `docs/EXPERIMENTS.md` — evidence log for real experiments.
- `docs/ROADMAP.md` — later phases, explicitly out of scope now.

## Current limitations

This is a local sandbox, not a production-secure deployment. It uses the local user's kubeconfig and kubectl subprocess, has no customer identity model, no MetaMynd authorization, no audit backend, and no endurance/chaos controller. The OpenTelemetry Demo is a representative workload, not a customer environment.

