from enum import StrEnum

from .models import ServiceObservation


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


def classify(observation: ServiceObservation) -> HealthState:
    if observation.desired_replicas < 0:
        return HealthState.UNKNOWN
    if observation.desired_replicas == 0:
        return HealthState.UNHEALTHY
    if observation.ready_replicas == observation.desired_replicas and observation.available_replicas == observation.desired_replicas and all(p["phase"] == "Running" and p["ready"] for p in observation.pods):
        return HealthState.HEALTHY
    if observation.ready_replicas > 0 or observation.available_replicas > 0:
        return HealthState.DEGRADED
    return HealthState.UNHEALTHY
