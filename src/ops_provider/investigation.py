from dataclasses import asdict

from .kubernetes import KubernetesProvider


def build_investigation(provider: KubernetesProvider, service: str, transition: dict | None = None) -> dict:
    """Bounded evidence package for future reasoning; no arbitrary Kubernetes access."""
    observation = provider.observe_service(service, tail_lines=80)
    return {"service": service, "observation": asdict(observation), "recent_transition": transition}


def build_reasoning_brief(investigation: dict) -> dict:
    """Deterministically compact complete evidence for the reasoning provider."""
    observation = investigation.get("observation", {})
    pods = observation.get("pods", [])
    transition = investigation.get("recent_transition") or {}
    transition_observation = transition.get("transition", transition) if isinstance(transition, dict) else {}
    transition_summary = {
        "fault": transition.get("fault") if isinstance(transition, dict) else None,
        "observed_at": transition_observation.get("observed_at"),
        "replicas": {key: transition_observation.get(key) for key in ("desired_replicas", "ready_replicas", "available_replicas")},
    }
    return {
        "incident_id": investigation.get("incident_id"),
        "service": investigation.get("service"),
        "observed_at": observation.get("observed_at"),
        "health_transition": transition_summary,
        "replicas": {key: observation.get(key) for key in ("desired_replicas", "ready_replicas", "available_replicas")},
        "pods": [{key: pod.get(key) for key in ("name", "phase", "ready", "restarts")} for pod in pods[:5]],
        "warnings": observation.get("warnings", [])[:5],
        "logs": observation.get("logs", "")[-1200:],
        "evidence_gaps": ["service reachability is not collected by the current provider"],
        "risk_context": investigation.get("risk_context"),
    }
