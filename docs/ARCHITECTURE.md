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

## Observation and evidence path

```text
KubernetesProvider.observe_service
        |
        v
bounded ServiceObservation -> deterministic classifier -> SQLite EvidenceStore
                                      |
                                      +-> incident + investigation package

test-only ScenarioHarness -> real reversible fault -> same observation path -> evaluator
```

The monitor collects only selected deployment, pod, restart-count, warning-event and log
fields. It does not grant the future reasoning agent raw Kubernetes access. Scenario
injection is intentionally separate and privileged for test ground truth; it is not
registered as an operational tool.

## Bounded reasoning path

```text
investigation package (DATA)
        -> ReasoningProvider
        -> strict OperationalDecision validation
        -> OBSERVE | ESCALATE | ACT
        -> GovernedOperations -> MetaMynd -> KubernetesProvider
        -> post-action observation + evidence
```

The decision parser validates only whether a proposed bounded tool call is
structurally executable. It does not decide whether the action is wise,
necessary, or delegated. A well-formed proposal is preserved and sent to
MetaMynd unchanged; operational quality is measured independently by the
evaluator. See `docs/VALIDATION_BOUNDARY.md`.

The reasoning provider has no shell, kubectl, Docker, credential or arbitrary HTTP tool.
The local Ollama provider is selectable by model name; an OpenAI Responses provider is
available only when an API key is explicitly supplied. Both return untrusted text that
must pass the decision schema. The agent chooses the operational action; MetaMynd does
not diagnose or choose the action, but independently enforces delegated authority.

## MetaMynd insertion point

Before either write method executes, `MetaMyndAuthorizer` sends the typed action/resource request through the official Node SDK in remote mode. Only `allow` and `observe` reach `KubernetesProvider`; `block`, `escalate`, malformed results, and transport failures stop before Kubernetes. This repository does not implement a fake authorization decision.

## Real versus synthetic

- Real: Docker, kind, Kubernetes resources, OpenTelemetry Demo images, pod state, deployment rollouts, scaling, and logs.
- Synthetic: unit-test subprocess runner responses only.
- Not implemented: autonomous reasoning, OpenRig, customer adapters, cloud APIs, frontend, MetaMynd, and production RBAC/security hardening.
