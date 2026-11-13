# Architecture

## Boundary

The future agent should request a typed operation, not execute shell commands. In Phase 1, the call path is:

```text
Operations call
  -> OperationsProvider protocol
  -> MetaMyndAuthorizer (official Node SDK, remote gate)
  -> GovernedOperations
  -> KubernetesProvider
  -> fixed kubectl invocation
  -> Kubernetes API
  -> real ops-sandbox resource
```

The provider is restricted to `ops-sandbox`, validates Kubernetes DNS resource names, caps scale at ten replicas, and exposes only read operations plus `restart_service` and `scale_service`. There is no arbitrary command method. `GovernedOperations` is the application-facing write path.

## MetaMynd insertion point

Before either write method executes, `MetaMyndAuthorizer` sends the typed action/resource request through the official Node SDK in remote mode. Only `allow` and `observe` reach `KubernetesProvider`; `block`, `escalate`, malformed results, and transport failures stop before Kubernetes. This repository does not implement a fake authorization decision.

## Real versus synthetic

- Real: Docker, kind, Kubernetes resources, OpenTelemetry Demo images, pod state, deployment rollouts, scaling, and logs.
- Synthetic: unit-test subprocess runner responses only.
- Not implemented: autonomous reasoning, OpenRig, customer adapters, cloud APIs, frontend, MetaMynd, and production RBAC/security hardening.
