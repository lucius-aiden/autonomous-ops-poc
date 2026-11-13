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


class ScaledToZeroScenario:
    """Test-only non-self-healing fault; remediation would be service.scale."""

    def __init__(self, provider: KubernetesProvider, service: str = "frontend"):
        self.provider, self.service, self.original = provider, service, None

    def setup(self) -> dict:
        self.original = self.provider.observe_service(self.service)
        if self.original.desired_replicas < 1 or self.original.ready_replicas != self.original.desired_replicas:
            raise RuntimeError("scenario requires a healthy replicated service")
        return {"service": self.service, "original_replicas": self.original.desired_replicas, "health": self.original}

    def inject(self) -> dict:
        if self.original is None:
            raise RuntimeError("setup must run first")
        self.provider.scale_service(self.service, 0)
        return {"fault": "deployment_scaled_to_zero", "service": self.service, "original_replicas": self.original.desired_replicas}

    def cleanup(self) -> dict:
        if self.original is None:
            raise RuntimeError("setup must run first")
        self.provider.scale_service(self.service, self.original.desired_replicas)
        deadline = time.time() + 120
        while time.time() < deadline:
            current = self.provider.observe_service(self.service)
            if current.ready_replicas == self.original.desired_replicas and current.available_replicas == self.original.desired_replicas:
                return {"cleaned": True, "health": current}
            time.sleep(2)
        raise RuntimeError("scale-to-zero cleanup timed out")


def scenario_id() -> str:
    return f"scenario-{uuid.uuid4().hex[:12]}"
