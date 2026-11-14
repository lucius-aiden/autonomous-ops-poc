"""Bounded tools exposed to an interactive reasoning agent.

Only read operations are registered here. Consequential operations remain on
the governed application path and are never reachable as raw provider calls.
"""

from dataclasses import asdict

from .kubernetes import KubernetesProvider


class ToolContractError(ValueError):
    pass


class ReadOnlyToolRegistry:
    """Structural tool boundary for agent-selected observation requests."""

    TOOLS = {"inspect_service", "get_service_health", "get_pods", "get_logs"}

    def __init__(self, provider: KubernetesProvider, max_log_lines: int = 100):
        self.provider = provider
        self.max_log_lines = max_log_lines

    def call(self, name: str, arguments: dict) -> dict:
        if name not in self.TOOLS:
            raise ToolContractError("unsupported or consequential tool")
        if not isinstance(arguments, dict):
            raise ToolContractError("tool arguments must be an object")
        service = arguments.get("service")
        if not isinstance(service, str):
            raise ToolContractError("service is required")
        if name == "inspect_service":
            if set(arguments) != {"service"}:
                raise ToolContractError("inspect_service has unsupported arguments")
            value = self.provider.observe_service(service)
            return asdict(value)
        if name == "get_service_health":
            if set(arguments) != {"service"}:
                raise ToolContractError("get_service_health has unsupported arguments")
            return self.provider.get_service_health(service)
        if name == "get_pods":
            if set(arguments) != {"service"}:
                raise ToolContractError("get_pods has unsupported arguments")
            return {"pods": self.provider.get_pods(service)}
        tail = arguments.get("tail_lines", 40)
        if set(arguments) - {"service", "tail_lines"} or not isinstance(tail, int) or not 1 <= tail <= self.max_log_lines:
            raise ToolContractError("tail_lines is outside the bounded log contract")
        return {"logs": self.provider.get_logs(service, tail)}
