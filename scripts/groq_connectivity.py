"""Groq schema preflight and three-call structured-output smoke test."""
import json
import sys
import time

from ops_provider.groq import GroqReasoningProvider


INVESTIGATION = {"service": "frontend", "observation": {"desired_replicas": 1, "ready_replicas": 1, "available_replicas": 1, "pods": [], "warnings": [], "logs": ""}, "recent_transition": None}


def main():
    provider = GroqReasoningProvider()
    results = []
    for index in range(4):
        started = time.perf_counter()
        try:
            decision = provider.decide(INVESTIGATION)
            results.append({"call": index + 1, "success": True, "schema_valid": True, "decision": decision.decision, "latency_seconds": time.perf_counter() - started})
        except Exception as error:
            results.append({"call": index + 1, "success": False, "schema_valid": False, "error_type": type(error).__name__, "error": str(error), "latency_seconds": time.perf_counter() - started})
            break
    print(json.dumps({"model": provider.model, "preflight": results[0], "three_call_smoke": results[1:] if results and results[0]["success"] else [], "all_passed": len(results) == 4 and all(x["success"] for x in results)}))
    return 0 if len(results) == 4 and all(x["success"] for x in results) else 1


if __name__ == "__main__":
    sys.exit(main())
