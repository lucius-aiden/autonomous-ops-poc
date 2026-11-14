# Validation boundary

`OperationalDecision` performs structural/tool-contract validation before a
consequential request reaches the governance adapter. It rejects malformed
JSON, unknown decision/tool names, missing required fields, invalid types,
unrepresentable Kubernetes targets, and action-specific parameter shapes that
the bounded executor cannot call safely.

It does not decide whether an action is wise, necessary, low risk, or delegated.
For example, `service.scale(frontend, replicas=5)` is structurally executable
and is sent unchanged to MetaMynd even when the current mandate blocks scale.
The Kubernetes provider's fixed namespace, DNS-name validation, and 0–10
replica execution cap are executor/tool bounds, not authority judgments.

MetaMynd is the authority boundary. BLOCK, ESCALATE, malformed verdicts and
transport failures stop execution. The evaluator separately judges operational
correctness and recovery; it cannot rewrite an agent decision or prevent an
otherwise authorized bounded operation retroactively.

Rules intentionally retained:

- parseable, complete decision object;
- known `OBSERVE`, `ACT`, and `ESCALATE` forms;
- known bounded tools (`service.restart`, `service.scale`);
- valid target representation and parameter types/ranges;
- action/parameter consistency required to invoke the executor safely.

No application policy rule was removed in this audit: the existing checks were
tool-contract bounds. No local check compares a proposal against the mandate or
substitutes a safer action. Operational judgment remains with the agent and
evaluator; authority judgment remains with MetaMynd.
