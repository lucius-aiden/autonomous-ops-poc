"""Bounded agent/tool trajectory orchestration.

This module deliberately contains orchestration limits and tool-contract
checks, not operational policy. The agent chooses read tools and its final
proposal; MetaMynd remains the authority gate for writes.
"""

import time
from dataclasses import asdict

from .agent_tools import ReadOnlyToolRegistry, ToolContractError
from .governed import GovernanceDenied, GovernedOperations
from .health import classify
from .kubernetes import KubernetesProvider
from .reasoning import InvalidDecision, OperationalDecision


class InteractiveLoopLimit(RuntimeError):
    pass


class BoundedInteractiveAgentLoop:
    def __init__(self, reasoning, provider: KubernetesProvider, governed: GovernedOperations,
                 tools: ReadOnlyToolRegistry | None = None, max_steps: int = 5,
                 max_model_calls: int = 6, max_elapsed_seconds: float = 60.0):
        self.reasoning = reasoning
        self.provider = provider
        self.governed = governed
        self.tools = tools or ReadOnlyToolRegistry(provider)
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls
        self.max_elapsed_seconds = max_elapsed_seconds

    def run(self, initial_observation: dict) -> dict:
        started = time.monotonic()
        state = {"initial_observation": initial_observation, "tool_results": []}
        trajectory = [{"kind": "initial_observation", "value": initial_observation}]
        model_calls = 0
        for step in range(self.max_steps):
            if time.monotonic() - started >= self.max_elapsed_seconds or model_calls >= self.max_model_calls:
                return self._stopped(trajectory, "orchestration_limit")
            if not hasattr(self.reasoning, "decide_turn"):
                return self._stopped(trajectory, "provider_does_not_support_interactive_turns")
            model_calls += 1
            try:
                turn = self.reasoning.decide_turn(state)
            except Exception as error:
                return self._stopped(trajectory, "reasoning_error", str(error))
            trajectory.append({"kind": "model_decision", "step": step, "value": turn})
            if not isinstance(turn, dict) or turn.get("type") not in {"tool", "final"}:
                return self._stopped(trajectory, "malformed_turn")
            if turn["type"] == "tool":
                if time.monotonic() - started >= self.max_elapsed_seconds:
                    return self._stopped(trajectory, "orchestration_limit")
                try:
                    result = self.tools.call(turn.get("tool"), turn.get("arguments"))
                except (ToolContractError, ValueError, RuntimeError) as error:
                    trajectory.append({"kind": "tool_error", "tool": turn.get("tool"), "error": str(error)})
                    return self._stopped(trajectory, "tool_contract_error", str(error))
                state["tool_results"].append({"tool": turn["tool"], "result": result})
                trajectory.append({"kind": "tool_result", "tool": turn["tool"], "value": result})
                continue
            try:
                decision = OperationalDecision.from_dict(turn.get("decision"))
            except (InvalidDecision, TypeError) as error:
                return self._stopped(trajectory, "invalid_final_decision", str(error))
            return self._execute(decision, trajectory)
        return self._stopped(trajectory, "orchestration_limit")

    def _execute(self, decision: OperationalDecision, trajectory: list[dict]) -> dict:
        result = {"status": "completed", "decision": asdict(decision), "trajectory": trajectory,
                  "governance": None, "execution": None, "verification": None}
        if decision.decision != "ACT":
            return result
        try:
            if decision.requested_action == "service.restart":
                executed = self.governed.restart_service(decision.target, decision.parameters.get("context"))
            elif decision.requested_action == "service.scale":
                executed = self.governed.scale_service(decision.target, decision.parameters["replicas"], decision.parameters.get("context"))
            else:
                raise InvalidDecision("unsupported consequential action")
            result["governance"], result["execution"] = executed["authorization"], executed["operation"]
            observation = self.provider.observe_service(decision.target)
            result["verification"] = {"health": classify(observation).value, "observation": asdict(observation)}
        except GovernanceDenied as denied:
            result["governance"] = denied.decision
        return result

    @staticmethod
    def _stopped(trajectory: list[dict], reason: str, error: str | None = None) -> dict:
        value = {"status": "stopped", "stop_reason": reason, "trajectory": trajectory}
        if error:
            value["error"] = error
        return value
