"""Real bounded-agent experiments using local Ollama plus real MetaMynd/Kubernetes."""
import atexit
import json
import sys
import time
import os
from datetime import datetime, timezone

from ops_provider.agent_loop import BoundedAgentLoop
from ops_provider.evidence import EvidenceStore
from ops_provider.investigation import build_investigation
from ops_provider.investigation import build_reasoning_brief
from ops_provider.kubernetes import KubernetesProvider
from ops_provider.monitor import OperationsMonitor
from ops_provider.reasoning import OllamaReasoningProvider
from ops_provider.scenarios import PodTerminationScenario, ScaledToZeroScenario, scenario_id
from ops_provider.governed import GovernedOperations, MetaMyndAuthorizer


def wait_for_detection(monitor, service, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = monitor.collect_once()[0]
        if result["health"] != "HEALTHY":
            return result
        time.sleep(1)
    return None


def run_one(label, scenario, model):
    started = time.perf_counter()
    provider = KubernetesProvider()
    store = EvidenceStore("data/ops-evidence.sqlite3")
    monitor = OperationsMonitor(provider, store, [scenario.service])
    governed = GovernedOperations(provider, MetaMyndAuthorizer())
    loop = BoundedAgentLoop(model, provider, governed)
    cleanup_needed = True
    atexit.register(lambda: scenario.cleanup() if cleanup_needed else None)
    initial = scenario.setup()
    fault_at = datetime.now(timezone.utc).isoformat()
    monitor.collect_once()
    fault = scenario.inject()
    detected = wait_for_detection(monitor, scenario.service)
    if detected is None:
        raise RuntimeError(f"{label}: detection timeout")
    investigation = build_investigation(provider, scenario.service, {"fault": fault, "transition": detected.get("observation", {})})
    investigation_at = datetime.now(timezone.utc).isoformat()
    reasoning_started = time.perf_counter()
    result = loop.handle(investigation)
    reasoning_completed = time.perf_counter()
    cleaned = scenario.cleanup()
    cleanup_needed = False
    verified = provider.observe_service(scenario.service)
    return {"experiment": label, "scenario_id": scenario_id(), "timestamps": {"fault": fault_at, "investigation_completed": investigation_at, "reasoning_seconds": reasoning_completed - reasoning_started, "total_seconds": time.perf_counter() - started}, "reasoning_brief": build_reasoning_brief(investigation), "initial": {"desired": initial["health"].desired_replicas, "ready": initial["health"].ready_replicas}, "fault": fault, "detected": detected["health"], "agent": result["decision"], "governance": result["governance"], "execution": result["execution"], "verification": {"desired": verified.desired_replicas, "ready": verified.ready_replicas}, "cleanup": cleaned["cleaned"]}


def main():
    model = OllamaReasoningProvider(model=os.environ.get("OPS_REASONING_MODEL", "gemma2:2b"))
    provider = KubernetesProvider()
    outputs = []
    # AGENT-001: platform self-healing. The model receives the investigation after a real pod fault.
    outputs.append(run_one("AGENT-001", PodTerminationScenario(provider, "frontend"), model))
    if os.environ.get("OPS_AGENT_ONLY") == "AGENT-001":
        print(json.dumps(outputs, indent=2, default=str))
        return
    # AGENT-002/003: real non-self-healing fault; scale is intentionally undelegated.
    outputs.append(run_one("AGENT-002/003", ScaledToZeroScenario(provider, "frontend"), model))
    print(json.dumps(outputs, indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"AGENT EXPERIMENT FAILED: {error}", file=sys.stderr)
        raise
