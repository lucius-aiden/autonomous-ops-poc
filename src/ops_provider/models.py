from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperationResult:
    operation: str
    resource: str
    namespace: str
    changed: bool
    data: Any

