"""Minimal Gemini connectivity and decision-schema preflight; never prints secrets."""
import json
import sys
import time

from ops_provider.gemini import GeminiReasoningProvider


def main():
    started = time.perf_counter()
    model = GeminiReasoningProvider()
    try:
        decision = model.decide({"service": "frontend", "observation": {"desired_replicas": 1, "ready_replicas": 1, "available_replicas": 1, "pods": [], "warnings": [], "logs": ""}, "recent_transition": None})
        print(json.dumps({"model": model.model, "success": True, "latency_seconds": time.perf_counter() - started, "schema_valid": True, "decision": decision.decision}))
    except Exception as error:
        print(json.dumps({"model": model.model, "success": False, "latency_seconds": time.perf_counter() - started, "schema_valid": False, "error_type": type(error).__name__, "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
