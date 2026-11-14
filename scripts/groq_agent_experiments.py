"""Real Groq bounded-agent experiments against the local Kubernetes sandbox."""
import atexit
import json
import os
import sys
import time
from datetime import datetime, timezone

from ops_provider.agent_loop import BoundedAgentLoop
from ops_provider.evidence import EvidenceStore
from ops_provider.governed import GovernedOperations, MetaMyndAuthorizer
from ops_provider.investigation import build_investigation, build_reasoning_brief
from ops_provider.kubernetes import KubernetesProvider
from ops_provider.monitor import OperationsMonitor
from ops_provider.groq import GroqReasoningProvider
from ops_provider.scenarios import PodTerminationScenario, ScaledToZeroScenario, scenario_id


def wait_for_detection(monitor, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = monitor.collect_once()[0]
        if result["health"] != "HEALTHY": return result
        time.sleep(1)
    return None


def run_one(label, scenario, risk_context=None):
    started = time.perf_counter(); provider = KubernetesProvider(); store = EvidenceStore("data/ops-evidence.sqlite3")
    monitor = OperationsMonitor(provider, store, [scenario.service]); model = GroqReasoningProvider()
    loop = BoundedAgentLoop(model, provider, GovernedOperations(provider, MetaMyndAuthorizer()))
    cleanup_needed = True; atexit.register(lambda: scenario.cleanup() if cleanup_needed else None)
    initial = scenario.setup(); fault_at = datetime.now(timezone.utc).isoformat(); monitor.collect_once(); fault = scenario.inject()
    inject_done = time.perf_counter(); detected = wait_for_detection(monitor)
    if detected is None: raise RuntimeError(f"{label}: detection timeout")
    detected_at = time.perf_counter(); investigation = build_investigation(provider, scenario.service, {"fault": fault, "transition": detected.get("observation", {})})
    if risk_context: investigation["risk_context"] = risk_context
    investigation_done = time.perf_counter()
    reasoning_error = None
    try:
        result = loop.handle(investigation)
    except Exception as error:
        # Invalid model output is evidence and must fail closed, not abort the
        # remaining independent experiments.
        reasoning_error = {"type": type(error).__name__, "message": str(error)}
        result = {"decision": None, "governance": None, "execution": None, "verification": None}
    reasoning_done = time.perf_counter()
    cleaned = scenario.cleanup(); cleanup_needed = False; verified = provider.observe_service(scenario.service); finished = time.perf_counter()
    return {"experiment": label, "scenario_id": scenario_id(), "reasoning_brief": build_reasoning_brief(investigation), "raw_model_json": model.last_raw, "normalized_decision": result["decision"], "reasoning_failure": reasoning_error, "governance": result["governance"], "execution": result["execution"], "verification": result["verification"], "cleanup": cleaned["cleaned"], "initial": {"desired": initial["health"].desired_replicas, "ready": initial["health"].ready_replicas}, "fault": fault, "detected": detected["health"], "final_state": {"desired": verified.desired_replicas, "ready": verified.ready_replicas}, "timings_seconds": {"detection": detected_at-inject_done, "investigation": investigation_done-detected_at, "reasoning_and_governance": reasoning_done-investigation_done, "post_action_recovery_and_cleanup": finished-reasoning_done, "total": finished-started}}


def main():
    provider = KubernetesProvider(); outputs = []
    selected = os.environ.get("OPS_AGENT_ONLY")
    if not selected or selected == "AGENT-001": outputs.append(run_one("AGENT-001", PodTerminationScenario(provider, "frontend")))
    if not selected or selected == "AGENT-003": outputs.append(run_one("AGENT-003", ScaledToZeroScenario(provider, "frontend")))
    if not selected or selected == "AGENT-004": outputs.append(run_one("AGENT-004", PodTerminationScenario(provider, "frontend"), {"riskLevel": "high"}))
    print(json.dumps({"model": "openai/gpt-oss-20b", "experiments": outputs, "AGENT-002": {"status": "NOT_RUN", "reason": "No existing sound persistent restart-remediable sandbox scenario; no artificial fault was introduced."}}, indent=2, default=str))


if __name__ == "__main__":
    try: main()
    except Exception as error: print(f"GROQ AGENT EXPERIMENT FAILED: {type(error).__name__}: {error}", file=sys.stderr); raise
