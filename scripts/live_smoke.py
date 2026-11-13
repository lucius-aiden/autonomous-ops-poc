"""Real-cluster Phase 1 experiment: inspect, restart, scale, fail, recover."""
import json
import sys
import time

from ops_provider import KubernetesProvider


def wait_ready(provider, name, expected, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = provider.get_service_health(name)
        if state["ready"] == expected and state["healthy"]:
            return state
        time.sleep(3)
    raise RuntimeError(f"timed out waiting for {name}: {provider.get_service_health(name)}")


def main():
    provider = KubernetesProvider()
    service = "frontend"
    initial = provider.get_service_health(service)
    if not initial["healthy"] or initial["desired"] < 1:
        raise RuntimeError(f"frontend is not initially healthy: {initial}")
    pods_before = provider.get_pods(service)
    logs = provider.get_logs(service, 20)
    print(json.dumps({"step": "discover", "health": initial, "pods": pods_before, "logs_tail_lines": len(logs.splitlines())}, indent=2))

    provider.restart_service(service)
    restarted = wait_ready(provider, service, initial["desired"])
    pods_after = provider.get_pods(service)
    print(json.dumps({"step": "restart", "health": restarted, "pod_names_changed": {p["name"] for p in pods_before} != {p["name"] for p in pods_after}}, indent=2))

    target = 2 if initial["desired"] == 1 else 1
    provider.scale_service(service, target)
    scaled = wait_ready(provider, service, target)
    print(json.dumps({"step": "scale_up", "health": scaled, "pod_count": len(provider.get_pods(service))}, indent=2))
    provider.scale_service(service, initial["desired"])
    restored = wait_ready(provider, service, initial["desired"])
    print(json.dumps({"step": "scale_restore", "health": restored}, indent=2))

    provider.scale_service(service, 0)
    time.sleep(5)
    failed = provider.get_service_health(service)
    observed_failure = not failed["healthy"] and failed["ready"] == 0
    print(json.dumps({"step": "controlled_failure", "health": failed, "degradation_observed": observed_failure}, indent=2))
    provider.scale_service(service, initial["desired"])
    recovered = wait_ready(provider, service, initial["desired"])
    print(json.dumps({"step": "recovery", "health": recovered, "recovered": recovered["healthy"]}, indent=2))
    if not observed_failure:
        raise RuntimeError("controlled failure was not observed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"LIVE SMOKE FAILED: {error}", file=sys.stderr)
        raise

