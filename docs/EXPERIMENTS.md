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

## MM-K8S-001 — hosted authorized restart

- **Timestamp:** 2026-11-13 (UTC)
- **Requested action/resource:** `service.restart` / `frontend`
- **MetaMynd verdict:** `allow`, `AUTHORIZED`; authorization ID recorded by the CLI.
- **Infrastructure before:** deployment resourceVersion `8447`, replicas `1`, ready `1`, available `1`; pod `frontend-dd4779584-6fsqd`.
- **Infrastructure after:** resourceVersion `10750`, replicas `1`, ready `1`, available `1`; pod identity changed; operation returned `deployment.apps/frontend restarted`.
- **Result:** PASS. Real remote authorization preceded the real Kubernetes rollout.
- **Limitations:** the returned response did not include a public agent DID or evidence ID.

## MM-K8S-002 — scale authorization

- **Timestamp:** 2026-11-13 (UTC)
- **Requested action/resource:** `service.scale` / `frontend`, requested replicas `2`
- **MetaMynd verdict:** `block`, `NO_PERMISSION_FOR_ACTION`.
- **Infrastructure before/after:** resourceVersion `10750`, replicas `1`, ready `1`; unchanged.
- **Result:** BLOCKED as designed; no Kubernetes mutation occurred.
- **Required next step:** owner must add a narrow `service.scale` delegation/resource constraint in the MetaMynd dashboard before an authorized scale experiment can be run.

## MM-K8S-003 — undelegated action

- **Requested action/resource:** `permissions.update` / `frontend`
- **MetaMynd verdict:** `block`, `NO_PERMISSION_FOR_ACTION`.
- **Infrastructure before/after:** `10750:1:1:1` / `10750:1:1:1`.
- **Result:** PASS. The callable request was blocked before execution.

## MM-K8S-004 — fail closed

- **Requested action/resource:** `service.restart` / `frontend`, adapter path intentionally invalid.
- **Result:** PASS. The governed command exited non-zero with `GovernanceDenied`; deployment state remained `10750:1:1:1`.

## MM-K8S-005 — escalation

- **Requested action/resource:** `service.restart` / `frontend`, `riskLevel=high`.
- **MetaMynd verdict:** `escalate`, `RISK_REVIEW`, escalation ID recorded by the adapter.
- **Infrastructure before/after:** `10750:1:1:1` / `10750:1:1:1`.
- **Result:** PASS for zero mutation while pending. No approval was performed; no execution is claimed.

## OBS-001 — monitored pod termination lifecycle

- **Scenario ID:** `scenario-b866bb87c3ca`
- **Objective:** verify real fault observation, incident/evidence creation, investigation
  packaging and workload recovery without an agent remediation action.
- **Fault:** test-only harness deleted pod `frontend-79c594dcbc-nmsld` in `ops-sandbox`.
- **Detection:** classified `UNHEALTHY`; detection latency `0.819332s`.
- **Investigation:** collected bounded deployment/pod/restart/event/log evidence and stored
  it in SQLite; an incident was opened and later resolved.
- **Recovery:** Kubernetes recreated the pod; final state `1/1` healthy; recovery latency
  `3.580278s`.
- **Unexpected mutation:** false. The only intentional mutation was the harness pod delete.
- **Status:** PASS.
- **Limitation:** this tests detection and platform recovery, not diagnosis or authorized
  agent remediation.

## Agent reasoning milestone

- **Provider:** local Ollama, installed `gemma2:2b` and `qwen2.5:7b-instruct-q4_K_M` models.
- **Standalone provider smoke:** a compact real investigation produced a schema-valid
  `OBSERVE` decision from `gemma2:2b`; no infrastructure tool was available to that call.
- **AGENT-001/002/003 end-to-end status:** not passed. Real scenario calls with the full
  investigation package exceeded the local CPU model runtime timeout (300 seconds).
  The scenario harness cleanup ran and Kubernetes remained healthy (`1:1:1`) after each
  attempt. This is recorded as a runtime limitation, not converted into a synthetic pass.
- **Reasoning implementation status:** schema, prompt, provider interface, Ollama/OpenAI
  adapters, validation, ACT/OBSERVE/ESCALATE loop, governance handoff and post-action
  verification are implemented and unit-tested.
- **Intervention scenario:** scale-to-zero is implemented as a real non-self-healing
  harness scenario. Its appropriate remediation is `service.scale`, which MetaMynd
  correctly blocks under the unchanged mandate. A sound restart-remediable fault was not
  identified without constructing an artificial failure, so none was fabricated.

## Compact reasoning/runtime follow-up

- The deterministic `build_reasoning_brief()` now sends only incident/service, transition,
  replica counts, up to five pod summaries, up to five warnings, the last 1,200 log
  characters, timestamp and evidence gaps. Complete raw investigation evidence remains in
  SQLite.
- The compact brief measured approximately 2,495 characters on a worst-case 10,000-character
  log input.
- A standalone local `gemma2:2b` call produced a valid `OBSERVE` decision. No hosted model
  credential was configured.
- Repeated real AGENT-001 calls against the compact scenario brief still exceeded the
  300-second local CPU timeout. Cleanup ran and the cluster returned to `1:1:1` each time.
- Therefore AGENT-001/002/003/004 are not claimed as completed LLM end-to-end experiments.
  The bounded loop, timing fields, brief capture, governance handoff and verification path
  are implemented; the remaining blocker is inference runtime, not authorization.
