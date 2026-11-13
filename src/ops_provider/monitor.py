import time
import uuid
from dataclasses import asdict

from .evidence import EvidenceStore
from .health import HealthState, classify
from .kubernetes import KubernetesProvider


class OperationsMonitor:
    def __init__(self, provider: KubernetesProvider, store: EvidenceStore, services: list[str]):
        self.provider, self.store, self.services = provider, store, services
        self.previous: dict[str, HealthState] = {}

    def collect_once(self) -> list[dict]:
        results = []
        for service in self.services:
            observation = self.provider.observe_service(service)
            state = classify(observation)
            data = asdict(observation)
            self.store.record_event("observation", observation.observed_at, data, service, state.value)
            previous = self.previous.get(service)
            if previous != state:
                self.store.record_event("health_transition", observation.observed_at, {"from": previous, "to": state.value}, service, state.value)
                if state in {HealthState.DEGRADED, HealthState.UNHEALTHY}:
                    incident_id = f"inc-{uuid.uuid4().hex[:12]}"
                    self.store.open_incident(incident_id, observation.observed_at, service, "health classification changed", state.value, data)
                    data["incident_id"] = incident_id
            self.previous[service] = state
            results.append({"service": service, "health": state.value, "observation": data})
        return results

    def run(self, interval_seconds: float = 30.0, cycles: int | None = None):
        completed = 0
        while cycles is None or completed < cycles:
            self.collect_once()
            completed += 1
            if cycles is None or completed < cycles:
                time.sleep(interval_seconds)
