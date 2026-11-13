from dataclasses import dataclass
from typing import Any
from datetime import datetime, timezone


@dataclass(frozen=True)
class OperationResult:
    operation: str
    resource: str
    namespace: str
    changed: bool
    data: Any


@dataclass(frozen=True)
class ServiceObservation:
    observed_at: str
    service: str
    desired_replicas: int
    ready_replicas: int
    available_replicas: int
    pods: list[dict]
    warnings: list[dict]
    logs: str

    @classmethod
    def now(cls, service: str, **values: Any) -> "ServiceObservation":
        return cls(datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"), service, **values)
