"""Real test-harness lifecycle: delete one pod, observe, investigate, recover."""
import json
import sys
import time
import atexit
from datetime import datetime, timezone

from ops_provider.evidence import EvidenceStore
from ops_provider.evaluator import evaluate
from ops_provider.investigation import build_investigation
from ops_provider.kubernetes import KubernetesProvider
from ops_provider.monitor import OperationsMonitor
from ops_provider.scenarios import PodTerminationScenario, scenario_id


def main():
    provider = KubernetesProvider()
    store = EvidenceStore("data/ops-evidence.sqlite3")
    monitor = OperationsMonitor(provider, store, ["frontend"])
    scenario = PodTerminationScenario(provider, "frontend")
    sid = scenario_id()
    started = datetime.now(timezone.utc)
    initial = scenario.setup()
    baseline = monitor.collect_once()
    injected = scenario.inject()
    cleaned_flag = False
    def ensure_cleanup():
        nonlocal cleaned_flag
        if not cleaned_flag:
            try:
                scenario.cleanup()
                cleaned_flag = True
            except Exception as cleanup_error:
                print(f"SCENARIO CLEANUP FAILED: {cleanup_error}", file=sys.stderr)
    atexit.register(ensure_cleanup)
    detected = None
    investigation = None
    for _ in range(30):
        result = monitor.collect_once()[0]
        if result["health"] != "HEALTHY":
            detected = datetime.now(timezone.utc)
            investigation = build_investigation(provider, "frontend", {"scenario_id": sid, "fault": injected})
            store.record_event("investigation", investigation["observation"]["observed_at"], investigation, "frontend", result["health"])
            break
        time.sleep(1)
    cleaned = scenario.cleanup()
    cleaned_flag = True
    recovered = datetime.now(timezone.utc)
    final = monitor.collect_once()[0]
    incident_id = result.get("observation", {}).get("incident_id") if detected else None
    if incident_id:
        store.resolve_incident(incident_id, recovered.isoformat(), {"scenario_id": sid, "final_health": final["health"], "cleanup": cleaned["cleaned"]})
    evaluation = evaluate(sid, started, detected, detected is not None, investigation is not None, recovered, unexpected_mutation=False)
    print(json.dumps({"scenario_id": sid, "initial_healthy": baseline[0]["health"], "fault": injected, "detected_health": None if not detected else result["health"], "investigation_collected": investigation is not None, "cleanup": {"cleaned": cleaned["cleaned"], "final_health": final["health"]}, "evaluation": evaluation.__dict__, "evidence_events": len(store.events())}, indent=2, default=str))
    if not evaluation.detected or not evaluation.recovered or final["health"] != "HEALTHY":
        raise RuntimeError("scenario lifecycle did not satisfy detection/recovery requirements")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"SCENARIO FAILED: {error}", file=sys.stderr)
        raise
