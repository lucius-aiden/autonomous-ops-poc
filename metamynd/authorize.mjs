import { createGuardFromConfig } from '@metamynd/agentsafe-guard';

// Deliberately remote: local-only evaluation is not sufficient evidence for
// Phase 2's real testnet authorization experiments.
const config = process.env.METAMYND_CONFIG || './agent.metamynd.json';

function safeDecision(decision) {
  if (!decision || typeof decision !== 'object') throw new Error('malformed MetaMynd decision');
  const allowed = ['allow', 'observe', 'block', 'escalate'];
  if (!allowed.includes(decision.decision)) throw new Error('unknown MetaMynd disposition');
  return {
    decision: decision.decision,
    reasonCode: decision.reasonCode ?? null,
    reason: decision.reason ?? null,
    authorizationId: decision.authorizationId ?? null,
    escalationId: decision.escalationId ?? null,
    evidenceId: decision.evidenceId ?? decision.evidence?.id ?? null,
    agentDid: decision.agentDid ?? null,
  };
}

async function main() {
  let request;
  try { request = JSON.parse(await new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  })); } catch { throw new Error('invalid adapter request'); }
  if (!request || typeof request.action !== 'string' || typeof request.resource !== 'string') {
    throw new Error('action and resource are required');
  }
  const guard = await createGuardFromConfig(config, { mode: 'remote' });
  const result = await guard.authorize({
    action: request.action,
    resource: request.resource,
    context: request.context ?? { source: 'autonomous-ops-poc' },
  });
  process.stdout.write(JSON.stringify(safeDecision(result)) + '\n');
}

main().catch(error => {
  process.stderr.write(`MetaMynd adapter failed: ${error.message}\n`);
  process.exitCode = 1;
});
