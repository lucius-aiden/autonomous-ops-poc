# MetaMynd hosted Testnet setup

The repository pins `@metamynd/agentsafe-guard` **0.37.4**. The Node adapter loads
`agent.metamynd.json` with `createGuardFromConfig`, forces remote mode, and calls the
official `guard.authorize()` endpoint. Python `GovernedOperations` calls it before any
restart or scale mutation.

No MetaMynd owner credentials or hosted agent config were available to this run. In the
MetaMynd-owned environment, run the supported hosted flow in a separate scratch directory:

```bash
npx create-metamynd-agent@latest --non-financial --name "Autonomous Ops POC" \
  --scope service.restart --yes --out ./metamynd-agent
```

The scaffolder requires owner login and provisions a Testnet identity, mandate, SOP and
Standards. Configure the resulting agent so it delegates only `service.restart` and
`service.scale` for `ops-sandbox/frontend`, with the narrowest supported replica limit.
Leave an unknown action/resource undelegated for the BLOCK experiment. If the dashboard
is required to add resource constraints or `service.scale`, make that edit there.

Copy the generated config locally (never commit it; it can contain private key material):

```bash
cp /path/to/agent.metamynd.json ./agent.metamynd.json
PYTHONPATH=src python3 -m ops_provider.cli restart frontend
PYTHONPATH=src python3 -m ops_provider.cli scale frontend 2
```

Without this config, the governed CLI fails closed and does not touch Kubernetes. Do not
paste credentials, keys, or tokens into chat.

Real hosted-agent evidence is still required for MM-K8S-001/002 ALLOW mutations,
MM-K8S-003 BLOCK, MM-K8S-004 hosted transport failure, and conditional MM-K8S-005
escalation/approval.
