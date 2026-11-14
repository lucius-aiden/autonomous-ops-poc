# Reasoning evaluation

This is a reasoning-only fixture evaluation. It does not call MetaMynd, mutate
Kubernetes, or count as an infrastructure experiment. Hidden expectations live
in the evaluator, not in the investigation fixtures sent to the provider.

## Prompt and brief size

The compact brief now summarizes the transition (fault, timestamp and replica
counts) instead of embedding the complete transition observation a second time.
For the representative fixture used in this pass, the brief was measured at
1,806 characters and the full prompt at 3,463 characters. The prior brief
implementation was 3,167 characters for the same fixture because it repeated
the transition payload. Exact token counts vary by tokenizer; the live
Groq calls reported their own usage below.

The prompt was changed once before the pass to give general first-line operator
principles and capability semantics. It does not mention current authority,
mandates, or expected fixture answers and does not request chain-of-thought.

## One-pass results

Model: `openai/gpt-oss-20b`; five calls; no execution or MetaMynd access.

- HEALTHY: OBSERVE; structurally valid; operationally correct; 563 input / 267 output tokens; 0.434s.
- ACTIVE_RECOVERY: ESCALATE; structurally valid; operationally incorrect (expected OBSERVE); 573 / 613 tokens; 0.781s.
- PERSISTENT_UNAVAILABLE: ACT `service.restart` on `frontend`; structurally valid; operationally correct for the fixture class; 579 / 391 tokens; 0.486s.
- RESTART_APPROPRIATE: ACT `service.restart` on `frontend`; structurally valid; operationally correct; 582 / 480 tokens; 0.820s.
- INSUFFICIENT_EVIDENCE: ESCALATE; structurally valid; operationally correct; 546 / 507 tokens; 0.850s.

All five responses parsed and passed application validation. The main observed
failure was an escalation bias for active recovery; no malformed output or
excessive intervention occurred in this pass. This is not evidence of production
performance and was not repeated because the free-tier quota is limited.
