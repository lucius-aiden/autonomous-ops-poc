import unittest

from ops_provider.agent_tools import ReadOnlyToolRegistry, ToolContractError
from ops_provider.governed import GovernedOperations
from ops_provider.interactive_loop import BoundedInteractiveAgentLoop
from ops_provider.models import OperationResult, ServiceObservation


class Provider:
    def __init__(self): self.calls = []
    def observe_service(self, service):
        self.calls.append(("inspect", service))
        return ServiceObservation.now(service, desired_replicas=1, ready_replicas=1, available_replicas=1, pods=[], warnings=[], logs="ok")
    def get_service_health(self, service): self.calls.append(("health", service)); return {"name": service, "healthy": True}
    def get_pods(self, service): self.calls.append(("pods", service)); return []
    def get_logs(self, service, tail_lines=100): self.calls.append(("logs", service, tail_lines)); return "ok"
    def restart_service(self, service): self.calls.append(("restart", service)); return OperationResult("restart_service", service, "ops-sandbox", True, {})
    def scale_service(self, service, replicas): self.calls.append(("scale", service, replicas)); return OperationResult("scale_service", service, "ops-sandbox", True, {})


class Authorizer:
    def __init__(self, verdict): self.verdict, self.calls = verdict, []
    def authorize(self, action, resource, context=None): self.calls.append((action, resource)); return self.verdict


class Reasoning:
    def __init__(self, turns): self.turns = iter(turns)
    def decide_turn(self, state): return next(self.turns)


def final(decision="OBSERVE", action=None, target=None, parameters={}):
    return {"type": "final", "decision": {"decision": decision, "summary": "s", "diagnosis": "d", "confidence": .8, "requested_action": action, "target": target, "parameters": parameters, "reason": "r", "verification_plan": "v"}}


class InteractiveLoopTests(unittest.TestCase):
    def test_agent_selects_read_tools_and_receives_results(self):
        provider = Provider()
        result = BoundedInteractiveAgentLoop(Reasoning([{"type": "tool", "tool": "get_logs", "arguments": {"service": "frontend", "tail_lines": 10}}, final()]), provider, GovernedOperations(provider, Authorizer({"decision": "allow"}))).run({"trigger": "degraded"})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(provider.calls, [("logs", "frontend", 10)])
        self.assertEqual(result["trajectory"][-2]["kind"], "tool_result")

    def test_consequential_action_still_crosses_governance(self):
        provider, authorizer = Provider(), Authorizer({"decision": "allow"})
        result = BoundedInteractiveAgentLoop(Reasoning([final("ACT", "service.restart", "frontend", {})]), provider, GovernedOperations(provider, authorizer)).run({})
        self.assertEqual(authorizer.calls, [("service.restart", "frontend")])
        self.assertEqual(provider.calls[0], ("restart", "frontend"))

    def test_blocked_action_has_no_execution(self):
        provider, authorizer = Provider(), Authorizer({"decision": "block"})
        result = BoundedInteractiveAgentLoop(Reasoning([final("ACT", "service.scale", "frontend", {"replicas": 5})]), provider, GovernedOperations(provider, authorizer)).run({})
        self.assertEqual(result["governance"]["decision"], "block")
        self.assertEqual(provider.calls, [])

    def test_limit_stops_without_inventing_action(self):
        provider = Provider()
        result = BoundedInteractiveAgentLoop(Reasoning([{"type": "tool", "tool": "get_pods", "arguments": {"service": "frontend"}}]), provider, GovernedOperations(provider, Authorizer({"decision": "allow"})), max_steps=1).run({})
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_reason"], "orchestration_limit")
        self.assertEqual([c for c in provider.calls if c[0] in ("restart", "scale")], [])

    def test_unsupported_tool_fails_safely(self):
        with self.assertRaises(ToolContractError):
            ReadOnlyToolRegistry(Provider()).call("kubectl", {"service": "frontend"})


if __name__ == "__main__": unittest.main()
