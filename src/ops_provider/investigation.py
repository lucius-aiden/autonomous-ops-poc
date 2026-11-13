from dataclasses import asdict

from .kubernetes import KubernetesProvider


def build_investigation(provider: KubernetesProvider, service: str, transition: dict | None = None) -> dict:
    """Bounded evidence package for future reasoning; no arbitrary Kubernetes access."""
    observation = provider.observe_service(service, tail_lines=80)
    return {"service": service, "observation": asdict(observation), "recent_transition": transition}
