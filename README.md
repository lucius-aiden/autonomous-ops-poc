# Autonomous Ops POC

Phase 2 adds a real MetaMynd authorization boundary in front of consequential operations. It deliberately does **not** contain an LLM agent, OpenRig, frontend, customer connectors, or production-security claims.

## What Phase 1 proves

- A real single-node [kind](https://kind.sigs.k8s.io/) Kubernetes cluster can be recreated locally.
- The real OpenTelemetry Demo runs as Kubernetes workloads in `ops-sandbox`.
- Python operations tools inspect real cluster state and logs.
- The same constrained tool layer performs real deployment restart and scaling operations.
- A reversible scale-to-zero failure is observed and remediated through the tool layer.
- Application-facing restart/scale calls fail closed unless the remote MetaMynd gate returns `allow` or `observe`.
- A bounded monitor, deterministic health classifier, SQLite evidence store, investigation package, and isolated pod-fault scenario harness are included.
- A strict reasoning interface and local Ollama/OpenAI provider boundary are included; live end-to-end reasoning is runtime-dependent and never bypasses MetaMynd.

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

Run the real observation lifecycle against the local cluster:

```bash
PYTHONPATH=src python3 scripts/monitor_scenario.py
```

Before write commands, provision a hosted Testnet agent and place its local
`agent.metamynd.json` at the repository root. See `docs/METAMYND_SETUP.md`. Without that
file, the governed CLI intentionally fails closed.

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

`KubernetesProvider` executes only validated, namespace-scoped Kubernetes calls. `GovernedOperations` is the application-facing write boundary and invokes the official Node `@metamynd/agentsafe-guard@0.37.4` adapter in remote mode before execution. BLOCK, ESCALATE, malformed verdicts, and adapter failures execute no Kubernetes write.

## Repository layout

- `src/ops_provider/` — provider protocol, structured result model, constrained Kubernetes implementation, CLI.
- `metamynd/authorize.mjs` — minimal official SDK adapter; it does not implement MAGP signing.
- `src/ops_provider/monitor.py`, `health.py`, `investigation.py` — bounded observation and evidence preparation.
- `src/ops_provider/evidence.py` — local SQLite observations/transitions/incidents store.
- `src/ops_provider/scenarios.py` — test-only reversible fault injection, never an agent tool.
- `scripts/` — reproducible kind/Helm lifecycle and live experiment.
- `tests/` — unit tests; no live-cluster behavior is mocked into the experiment.
- `docs/ARCHITECTURE.md` — trust and execution boundary.
- `docs/EXPERIMENTS.md` — evidence log for real experiments.
- `docs/ROADMAP.md` — later phases, explicitly out of scope now.

## Current limitations

This is a local sandbox, not a production-secure deployment. It uses the local user's kubeconfig and kubectl subprocess, has no customer identity model or audit backend, and no endurance/chaos controller. Real hosted MetaMynd experiments remain pending agent provisioning.
