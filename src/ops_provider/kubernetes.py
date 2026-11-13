"""Constrained Kubernetes operations adapter.

Only fixed kubectl subcommands are reachable through this class. The future
MetaMynd authorization boundary belongs immediately before restart_service and
scale_service; this Phase 1 prototype intentionally does not implement policy.
"""

import json
import re
import subprocess
from typing import Sequence

from .models import OperationResult


_NAME = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
NAMESPACE = "ops-sandbox"


class KubernetesProvider:
    def __init__(self, namespace: str = NAMESPACE, runner=subprocess.run):
        if namespace != NAMESPACE:
            raise ValueError(f"provider is restricted to namespace {NAMESPACE!r}")
        self.namespace = namespace
        self._runner = runner

    def _name(self, value: str, label: str = "resource") -> str:
        if not isinstance(value, str) or not _NAME.fullmatch(value):
            raise ValueError(f"invalid {label} name")
        return value

    def _run(self, args: Sequence[str], *, json_output: bool = True) -> object:
        completed = self._runner(
            ["kubectl", *args], capture_output=True, text=True, check=False
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "kubectl failed")
        output = completed.stdout.strip()
        if not json_output:
            return output
        return json.loads(output) if output else {}

    def get_cluster_health(self) -> dict:
        nodes = self._run(["get", "nodes", "-o", "json"])
        return {
            "healthy": bool(nodes.get("items")) and all(
                any(c.get("type") == "Ready" and c.get("status") == "True" for c in n.get("status", {}).get("conditions", []))
                for n in nodes.get("items", [])
            ),
            "nodes": [n.get("metadata", {}).get("name") for n in nodes.get("items", [])],
        }

    def list_services(self) -> list[dict]:
        data = self._run(["-n", self.namespace, "get", "deployments", "-o", "json"])
        return [self._deployment(item) for item in data.get("items", [])]

    def get_service_health(self, service: str) -> dict:
        service = self._name(service, "service")
        data = self._run(["-n", self.namespace, "get", "deployment", service, "-o", "json"])
        return self._deployment(data)

    def get_pods(self, service: str) -> list[dict]:
        service = self._name(service, "service")
        data = self._run(["-n", self.namespace, "get", "pods", "-l", f"app.kubernetes.io/name={service}", "-o", "json"])
        return [
            {"name": p.get("metadata", {}).get("name"), "phase": p.get("status", {}).get("phase"), "ready": self._ready(p)}
            for p in data.get("items", [])
        ]

    def get_logs(self, service: str, tail_lines: int = 100) -> str:
        service = self._name(service, "service")
        if not isinstance(tail_lines, int) or not 1 <= tail_lines <= 1000:
            raise ValueError("tail_lines must be between 1 and 1000")
        return self._run(["-n", self.namespace, "logs", f"deployment/{service}", f"--tail={tail_lines}"], json_output=False)

    def restart_service(self, service: str) -> OperationResult:
        service = self._name(service, "service")
        # rollout restart emits human-readable status rather than JSON. Keep
        # the provider result structured without pretending that output is JSON.
        message = self._run(
            ["-n", self.namespace, "rollout", "restart", f"deployment/{service}"],
            json_output=False,
        )
        data = {"message": message}
        return OperationResult("restart_service", service, self.namespace, True, data)

    def scale_service(self, service: str, replicas: int) -> OperationResult:
        service = self._name(service, "service")
        if not isinstance(replicas, int) or not 0 <= replicas <= 10:
            raise ValueError("replicas must be an integer from 0 through 10")
        data = self._run(["-n", self.namespace, "scale", f"deployment/{service}", f"--replicas={replicas}", "-o", "json"])
        return OperationResult("scale_service", service, self.namespace, True, data)

    @staticmethod
    def _ready(pod: dict) -> bool:
        return any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", []))

    @staticmethod
    def _deployment(item: dict) -> dict:
        spec = item.get("spec", {})
        status = item.get("status", {})
        desired = spec.get("replicas", 0)
        ready = status.get("readyReplicas", 0)
        return {"name": item.get("metadata", {}).get("name"), "desired": desired, "ready": ready, "available": status.get("availableReplicas", 0), "healthy": desired > 0 and ready == desired}
