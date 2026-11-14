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

## Frozen-prompt consistency results

The prompt and runtime configuration were frozen at commit `fb6d381` for this
measurement. No prompt, fixture, evaluator, model, temperature, or provider
settings were changed between passes.

- Model: `openai/gpt-oss-20b`
- Response mode: Groq JSON Object Mode
- Temperature: `0`
- Provider: existing `GroqReasoningProvider`
- MetaMynd/Kubernetes access: none
- Total target: three observations per fixture, including the original pass

The original pass plus two additional passes produced 14 successful model
responses. The final INSUFFICIENT_EVIDENCE call was rejected by Groq HTTP 429
before generation, so it is recorded as unavailable rather than a decision.

| Fixture | Runs | Valid outputs | Decisions | Correct | Incorrect |
|---|---:|---:|---|---:|---:|
| HEALTHY | 3 | 3 | OBSERVE ×3 | 3 | 0 |
| ACTIVE_RECOVERY | 3 | 3 | ESCALATE ×3 | 0 | 3 |
| PERSISTENT_UNAVAILABLE | 3 | 3 | ACT/service.restart ×3 | 3 | 0 |
| RESTART_APPROPRIATE | 3 | 3 | ACT/service.restart ×3 | 3 | 0 |
| INSUFFICIENT_EVIDENCE | 3 | 2 | ESCALATE ×2; unavailable ×1 | 2 | 0 |
| **Total** | **15** | **14** | — | **11** | **3** |

Structural validity was **14/14 (100%)** among responses returned by the
model. Counting the rate-limited slot as an attempted fixture, availability was
**14/15**. Operational correctness was **11/14 (78.6%)** among valid outputs.
These are small-sample measurements, not statistically significant estimates.

Observed latency ranges for successful calls were approximately:

- HEALTHY: 0.412–0.674s
- ACTIVE_RECOVERY: 0.781–0.974s
- PERSISTENT_UNAVAILABLE: 0.487–1.011s
- RESTART_APPROPRIATE: 0.623–0.820s
- INSUFFICIENT_EVIDENCE: 0.850–0.995s

Prompt token counts were stable per fixture at 563, 573, 579, 582, and 546
respectively. Completion tokens varied with the model's response/reasoning;
the successful calls reported 267–656 completion tokens. Groq reported cached
prompt tokens on some later calls. No response was discarded for
inconsistency.

Groq rate limiting occurred on the third pass's final fixture:
HTTP 429, TPM limit 8,000, used 7,255, requested 1,082. The run stopped
without retrying or hammering the endpoint.

### Interpretation

ACTIVE_RECOVERY produced ESCALATE in all three valid observations, so the
original result is not isolated in this small sample. The other fixture classes
were stable and correct in the available observations. This supports one
general prompt adjustment focused on distinguishing visible recovery
convergence from genuinely insufficient evidence; it does not justify claims
of statistical significance or production reliability. No adjustment was made
in this measurement commit.

## Original one-pass details

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
