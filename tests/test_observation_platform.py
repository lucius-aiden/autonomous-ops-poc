import tempfile
import unittest
from pathlib import Path

from ops_provider.evidence import EvidenceStore
from ops_provider.health import HealthState, classify
from ops_provider.models import ServiceObservation


def observation(desired=1, ready=1, available=1, phase="Running", pod_ready=True):
    return ServiceObservation.now("frontend", desired_replicas=desired, ready_replicas=ready, available_replicas=available, pods=[{"name": "frontend-1", "phase": phase, "ready": pod_ready, "restarts": 0, "conditions": []}] if desired else [], warnings=[], logs="ok")


class ObservationPlatformTests(unittest.TestCase):
    def test_health_rules_are_deterministic(self):
        self.assertEqual(classify(observation()), HealthState.HEALTHY)
        self.assertEqual(classify(observation(ready=0, available=0, phase="Pending", pod_ready=False)), HealthState.UNHEALTHY)
        self.assertEqual(classify(observation(ready=1, available=0)), HealthState.DEGRADED)
        self.assertEqual(classify(observation(desired=0)), HealthState.UNHEALTHY)

    def test_evidence_store_persists_events_and_rejects_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(Path(directory) / "evidence.sqlite3")
            store.record_event("observation", observation().observed_at, {"health": "HEALTHY"}, "frontend", "HEALTHY")
            self.assertEqual(len(store.events()), 1)
            with self.assertRaises(ValueError):
                store.record_event("bad", observation().observed_at, {"agentKey": "secret"})


if __name__ == '__main__':
    unittest.main()
