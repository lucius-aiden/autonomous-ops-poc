# Current MetaMynd configuration (observed 2026-11-13)

This document records only public policy/identity metadata observed from the local
generated configuration and its public policy-bundle URL. Private key fields, tokens and
secret headers were not read into this document.

## Identity and principal

- Agent DID: `did:hedera:testnet:z69kfxLtup3mrUaFC4AKbvzPykQq8WQY8KtTnc1qa9NSM_0.0.10361974`
- Identity ID: `3e9a595e-aa8c-41f2-9465-81334277838c`
- Owner/principal DID: `did:hedera:testnet:zHwXNwqYdRRrF2LJhtKuP9iTfdGrJEHu9KcQhUKLicMvp_0.0.10380074`
- Policy issuer DID: observed in the signed public bundle; not repeated here because the
  operationally relevant relationship is the bundle's issuer → subject binding.
- API: MetaMynd Testnet API base `https://metamynd.ai/api/v1`.
- Key verification: the generated config reports `keyVerified: true`. Private key material
  remains local and ignored by Git.

## Mandate and SOP

- Mandate action: `service.restart` only.
- Mandate valid-from: `2026-11-13T05:17:26.583Z`.
- Mandate reference: the public Hashscan Testnet transaction reference in the signed bundle
  (available locally, not required for execution).
- SOP: `High-risk review`, SOP ID `f3024bc2-1d24-4952-8254-b068ab469f58`.
- SOP rule: `risk-at-or-above` level `high` → `escalate`, reason `RISK_REVIEW`.
- Resource constraints: the observed mandate constraint list is empty. The current
  authorization model therefore delegates the action name, not an explicit Kubernetes
  resource scope. The application still restricts Kubernetes to `ops-sandbox` and validates
  resource names; this is not equivalent to a MetaMynd resource constraint.
- Expiry: no expiry was present in the observed mandate document. Bundle max staleness is
  `PT10M`; this is bundle freshness, not a mandate expiry.
- Standards: none enforced in the observed bundle.
- Self-escalation: blocked; no matched self-escalation actions.

## Why observed decisions occur

- `service.restart` with `riskLevel=low` → `ALLOW / AUTHORIZED`: it matches the sole
  delegated action and does not trigger the high-risk SOP.
- `service.scale` → `BLOCK / NO_PERMISSION_FOR_ACTION`: it is absent from
  `allowed_actions` and no mandate delegates it.
- `permissions.update` → `BLOCK / NO_PERMISSION_FOR_ACTION`: it is also absent and is not
  a delegated operation.
- `service.restart` with `riskLevel=high` → `ESCALATE / RISK_REVIEW`: the action is
  delegated, but the SOP escalates high-risk requests before execution.

## How association was established

The hosted scaffolder created the identity/configuration and provisioned the mandate and
SOP in the owner principal's Testnet context. The public bundle binds `subject` to the
agent DID, `ownerPrincipal` to the principal DID, and includes the mandate/SOP IDs. The
exact internal onboarding transaction sequence beyond those signed/public fields is
UNKNOWN.

## Current boundary

The Python application calls the pinned Node AgentSafe adapter in remote mode before
consequential Kubernetes operations. BLOCK, ESCALATE, malformed responses and transport
failures execute no Kubernetes mutation. The test harness has separate privileged fault
injection code and is not exposed as an agent operation.
