"""Bounded agent/tool trajectory orchestration.

This module deliberately contains orchestration limits and tool-contract
checks, not operational policy. The agent chooses read tools and its final
proposal; MetaMynd remains the authority gate for writes.
"""

import time
from datetime import datetime, timezone
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
                 max_model_calls: int = 6, max_elapsed_seconds: float = 60.0,
                 evidence_store=None):
        self.reasoning = reasoning
        self.provider = provider
        self.governed = governed
        self.tools = tools or ReadOnlyToolRegistry(provider)
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls
        self.max_elapsed_seconds = max_elapsed_seconds
        self.evidence_store = evidence_store

    def run(self, initial_observation: dict) -> dict:
        started = time.monotonic()
        compact_initial = self._compact(initial_observation)
        state = {"initial_observation": compact_initial, "tool_results": []}
        trajectory = [{"kind": "initial_observation", "value": compact_initial}]
        model_calls = 0
        for step in range(self.max_steps):
            if time.monotonic() - started >= self.max_elapsed_seconds or model_calls >= self.max_model_calls:
                return self._record(self._stopped(trajectory, "orchestration_limit"))
            if not hasattr(self.reasoning, "decide_turn"):
                return self._record(self._stopped(trajectory, "provider_does_not_support_interactive_turns"))
            model_calls += 1
            try:
                turn = self.reasoning.decide_turn(state)
            except Exception as error:
                return self._record(self._stopped(trajectory, "reasoning_error", type(error).__name__))
            trajectory.append({"kind": "model_decision", "step": step, "value": turn})
            if not isinstance(turn, dict) or turn.get("type") not in {"tool", "final"}:
                return self._record(self._stopped(trajectory, "malformed_turn"))
            if turn["type"] == "tool":
                if time.monotonic() - started >= self.max_elapsed_seconds:
                    return self._record(self._stopped(trajectory, "orchestration_limit"))
                try:
                    result = self.tools.call(turn.get("tool"), turn.get("arguments"))
                except (ToolContractError, ValueError, RuntimeError) as error:
                    trajectory.append({"kind": "tool_error", "tool": turn.get("tool"), "error": str(error)})
                    return self._record(self._stopped(trajectory, "tool_contract_error", str(error)))
                compact_result = self._compact(result)
                state["tool_results"].append({"tool": turn["tool"], "result": compact_result})
                trajectory.append({"kind": "tool_result", "tool": turn["tool"], "value": compact_result})
                continue
            try:
                decision = OperationalDecision.from_dict(turn.get("decision"))
            except (InvalidDecision, TypeError) as error:
                return self._record(self._stopped(trajectory, "invalid_final_decision", str(error)))
            return self._record(self._execute(decision, trajectory))
        return self._record(self._stopped(trajectory, "orchestration_limit"))

    def _record(self, result: dict) -> dict:
        if self.evidence_store is not None:
            self.evidence_store.record_event("agent_trajectory", datetime.now(timezone.utc).isoformat(), result)
        return result

    @staticmethod
    def _compact(value):
        if not isinstance(value, dict):
            return value
        result = dict(value)
        if isinstance(result.get("logs"), str):
            result["logs"] = result["logs"][-2000:]
        if isinstance(result.get("observation"), dict):
            result["observation"] = BoundedInteractiveAgentLoop._compact(result["observation"])
        if isinstance(result.get("pods"), list):
            result["pods"] = result["pods"][:10]
        if isinstance(result.get("tool_results"), list):
            result["tool_results"] = [{"tool": item.get("tool"), "result": BoundedInteractiveAgentLoop._compact(item.get("result", {}))} for item in result["tool_results"]]
        return result

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
