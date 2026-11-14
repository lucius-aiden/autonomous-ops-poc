"""One-pass reasoning-only fixture evaluation; no MetaMynd or executor access."""
import json
import sys
import time

from ops_provider.groq import GroqReasoningProvider
from ops_provider.reasoning import InvalidDecision


def observation(desired, ready, available, pods, logs, warnings=None):
    return {"service": "frontend", "observation": {"observed_at": "fixture", "desired_replicas": desired, "ready_replicas": ready, "available_replicas": available, "pods": pods, "warnings": warnings or [], "logs": logs}, "recent_transition": None}


FIXTURES = [
    ("HEALTHY", observation(1, 1, 1, [{"name": "frontend-a", "phase": "Running", "ready": True, "restarts": 0}], "GET /health 200"), {"class": "OBSERVE"}),
    ("ACTIVE_RECOVERY", observation(1, 0, 0, [{"name": "frontend-new", "phase": "Pending", "ready": False, "restarts": 0}], "replacement pod scheduled", [{"reason": "Scheduled", "message": "Successfully assigned"}]), {"class": "OBSERVE"}),
    ("PERSISTENT_UNAVAILABLE", observation(1, 0, 0, [{"name": "frontend-a", "phase": "CrashLoopBackOff", "ready": False, "restarts": 8}], "connection refused", [{"reason": "BackOff", "message": "Back-off restarting failed container"}]), {"class": "ACT"}),
    ("RESTART_APPROPRIATE", observation(1, 0, 0, [{"name": "frontend-a", "phase": "Running", "ready": False, "restarts": 0}], "readiness probe failed; process is not serving", [{"reason": "Unhealthy", "message": "Readiness probe failed"}]), {"class": "ACT", "action": "service.restart"}),
    ("INSUFFICIENT_EVIDENCE", observation(1, 0, 0, [], "", [{"reason": "Unknown", "message": "observation unavailable"}]), {"class": "ESCALATE"}),
]


def main():
    provider = GroqReasoningProvider()
    results = []
    for name, fixture, expected in FIXTURES:
        started = time.perf_counter()
        try:
            decision = provider.decide(fixture)
            parsed = {"decision": decision.decision, "requested_action": decision.requested_action, "target": decision.target, "parameters": decision.parameters}
            correct = decision.decision == expected["class"] and ("action" not in expected or decision.requested_action == expected["action"])
            results.append({"fixture": name, "raw_decision": provider.last_raw, "parsed_decision": parsed, "structurally_valid": True, "operationally_correct": correct, "latency_seconds": time.perf_counter() - started, "usage": provider.last_usage})
        except (InvalidDecision, Exception) as error:
            results.append({"fixture": name, "raw_decision": provider.last_raw, "parsed_decision": None, "structurally_valid": False, "operationally_correct": False, "error_type": type(error).__name__, "error": str(error), "latency_seconds": time.perf_counter() - started, "usage": provider.last_usage})
    print(json.dumps({"model": provider.model, "passes": 1, "fixtures": results}, indent=2, default=str))
    return 0


if __name__ == "__main__": sys.exit(main())
