# Experiments

## EXP-001 — Phase 1 live operations lifecycle

- **Objective:** prove discovery, logs, restart, scale, controlled failure, and real recovery through the Python operations layer.
- **Starting state:** healthy `frontend` deployment in `ops-sandbox`, original replica count recorded by `KubernetesProvider`.
- **Actions:** inspect health/pods/logs; restart deployment; scale to two replicas (or one when already above one); restore; scale to zero; observe; restore original count.
- **Expected:** pod names change after restart; replica count changes after scale; scale-to-zero is unhealthy and observable; restoration returns Ready/Available to the original count.
- **Actual result:** PASS on 2026-11-13. The real cluster reported one healthy frontend replica and logs; restart changed the pod name while returning to Ready; scale changed the deployment to two Ready replicas and restored it to one; scale-to-zero produced `desired=0`, `ready=0`, `available=0`, `healthy=false`; scaling back to one returned `healthy=true`.
- **Evidence:** `PYTHONPATH=src python3 scripts/live_smoke.py` completed all six lifecycle steps against kind cluster `ops-poc`; `./scripts/sandbox-status.sh` showed the OpenTelemetry Demo workloads Running/Ready in `ops-sandbox`.
- **Status:** PASS.
- **Limitations:** this proves local Kubernetes execution only; it does not prove production authorization, customer isolation, or autonomous decision-making.

## Phase 2 governance experiments

| ID | Status | Reason |
|---|---|---|
| MM-K8S-001 | BLOCKED | Fresh hosted Testnet agent/config requires MetaMynd owner provisioning. |
| MM-K8S-002 | BLOCKED | Fresh hosted Testnet agent/config requires MetaMynd owner provisioning. |
| MM-K8S-003 | BLOCKED | Cannot claim a real MetaMynd BLOCK without the hosted agent. |
| MM-K8S-004 | READY LOCALLY | Python transport failure tests prove fail-closed control flow; hosted evidence is pending. |
| MM-K8S-005 | CONDITIONAL | Run only if the configured hosted mandate supports genuine escalation. |

The implementation is present, but no Phase 2 PASS is claimed until the real hosted
authorization response and Kubernetes mutation/non-mutation evidence are recorded.
