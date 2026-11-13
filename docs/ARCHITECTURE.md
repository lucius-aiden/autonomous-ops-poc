# Architecture

## Boundary

The future agent should request a typed operation, not execute shell commands. In Phase 1, the call path is:

```text
Operations call
  -> OperationsProvider protocol
  -> KubernetesProvider
  -> fixed kubectl invocation
  -> Kubernetes API
  -> real ops-sandbox resource
```

The provider is restricted to `ops-sandbox`, validates Kubernetes DNS resource names, caps scale at ten replicas, and exposes only read operations plus `restart_service` and `scale_service`. There is no arbitrary command method.

## MetaMynd insertion point

Before either write method executes, Phase 2 should pass a typed request and context through MetaMynd mandate/SOP authorization. An allowed request reaches `KubernetesProvider`; an escalation or block stops before Kubernetes. This repository does not implement a fake authorization decision.

## Real versus synthetic

- Real: Docker, kind, Kubernetes resources, OpenTelemetry Demo images, pod state, deployment rollouts, scaling, and logs.
- Synthetic: unit-test subprocess runner responses only.
- Not implemented: autonomous reasoning, OpenRig, customer adapters, cloud APIs, frontend, MetaMynd, and production RBAC/security hardening.

