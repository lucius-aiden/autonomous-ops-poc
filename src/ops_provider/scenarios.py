import time
import uuid

from .kubernetes import KubernetesProvider


class PodTerminationScenario:
    """Test-only fault injector; never exposed through the agent operations interface."""

    def __init__(self, provider: KubernetesProvider, service: str = "frontend"):
        self.provider, self.service = provider, service
        self.initial = None
        self.deleted = None

    def setup(self) -> dict:
        self.initial = self.provider.observe_service(self.service)
        if self.initial.desired_replicas < 1 or not self.initial.pods:
            raise RuntimeError("scenario requires a running replicated service")
        return {"service": self.service, "pod": self.initial.pods[0]["name"], "health": self.initial}

    def inject(self) -> dict:
        if self.initial is None:
            raise RuntimeError("setup must run first")
        pod = self.initial.pods[0]["name"]
        self.provider._run(["-n", self.provider.namespace, "delete", "pod", pod, "--wait=false"], json_output=False)
        self.deleted = pod
        return {"fault": "pod_deleted", "pod": pod}

    def cleanup(self, timeout: float = 120) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            current = self.provider.observe_service(self.service)
            if current.ready_replicas == current.desired_replicas and current.desired_replicas > 0:
                return {"cleaned": True, "health": current, "deleted_pod": self.deleted}
            time.sleep(2)
        raise RuntimeError("scenario cleanup timed out")


def scenario_id() -> str:
    return f"scenario-{uuid.uuid4().hex[:12]}"
