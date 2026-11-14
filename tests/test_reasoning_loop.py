import unittest

from ops_provider.agent_loop import BoundedAgentLoop
from ops_provider.governed import GovernedOperations
from ops_provider.models import OperationResult, ServiceObservation
from ops_provider.reasoning import InvalidDecision, OperationalDecision


def decision(**overrides):
    value = {"decision": "OBSERVE", "summary": "platform is recovering", "diagnosis": "replacement in progress", "confidence": 0.8, "requested_action": None, "target": None, "parameters": {}, "reason": "least disruptive", "verification_plan": "observe readiness"}
    value.update(overrides)
    return OperationalDecision.from_dict(value)


class FakeReasoning:
    def __init__(self, value): self.value = value
    def decide(self, investigation): return self.value


class FakeProvider:
    def __init__(self): self.calls = []
    def restart_service(self, service):
        self.calls.append(("restart", service))
        return OperationResult("restart_service", service, "ops-sandbox", True, {})
    def scale_service(self, service, replicas):
        self.calls.append(("scale", service, replicas))
        return OperationResult("scale_service", service, "ops-sandbox", True, {})
    def observe_service(self, service):
        return ServiceObservation.now(service, desired_replicas=1, ready_replicas=1, available_replicas=1, pods=[{"name": "frontend-1", "phase": "Running", "ready": True, "restarts": 0, "conditions": []}], warnings=[], logs="ok")


class FakeAuthorizer:
    def __init__(self, decision): self.decision, self.calls = decision, []
    def authorize(self, action, resource):
        self.calls.append((action, resource))
        return self.decision


class ReasoningLoopTests(unittest.TestCase):
    def test_schema_rejects_unsupported_action_and_bad_parameters(self):
        with self.assertRaises(InvalidDecision):
            decision(decision="ACT", requested_action="shell.exec", target="frontend")
        with self.assertRaises(InvalidDecision):
            decision(decision="ACT", requested_action="service.scale", target="frontend", parameters={"replicas": 99})

    def test_observe_never_calls_provider_write(self):
        provider = FakeProvider()
        result = BoundedAgentLoop(FakeReasoning(decision()), provider, GovernedOperations(provider, FakeAuthorizer({"decision": "allow"}))).handle({"logs": "data"})
        self.assertEqual(result["decision"]["decision"], "OBSERVE")
        self.assertEqual(provider.calls, [])

    def test_allow_act_executes_then_verifies(self):
        provider = FakeProvider()
        result = BoundedAgentLoop(FakeReasoning(decision(decision="ACT", summary="restart", requested_action="service.restart", target="frontend", parameters={})), provider, GovernedOperations(provider, FakeAuthorizer({"decision": "allow", "reasonCode": "AUTHORIZED"}))).handle({})
        self.assertEqual(provider.calls, [("restart", "frontend")])
        self.assertEqual(result["governance"]["decision"], "allow")
        self.assertEqual(result["verification"]["health"], "HEALTHY")

    def test_blocked_act_does_not_execute(self):
        provider = FakeProvider()
        result = BoundedAgentLoop(FakeReasoning(decision(decision="ACT", summary="scale", requested_action="service.scale", target="frontend", parameters={"replicas": 2})), provider, GovernedOperations(provider, FakeAuthorizer({"decision": "block", "reasonCode": "NO_PERMISSION_FOR_ACTION"}))).handle({})
        self.assertEqual(provider.calls, [])
        self.assertEqual(result["governance"]["decision"], "block")

    def test_well_formed_scale_outside_current_authority_reaches_metamynd_unchanged(self):
        provider = FakeProvider()
        authorizer = FakeAuthorizer({"decision": "block", "reasonCode": "NO_PERMISSION_FOR_ACTION"})
        proposal = decision(decision="ACT", summary="scale proposal", requested_action="service.scale", target="frontend", parameters={"replicas": 5})
        result = BoundedAgentLoop(FakeReasoning(proposal), provider, GovernedOperations(provider, authorizer)).handle({})
        self.assertEqual(authorizer.calls, [("service.scale", "frontend")])
        self.assertEqual(result["decision"]["requested_action"], "service.scale")
        self.assertEqual(result["decision"]["parameters"]["replicas"], 5)
        self.assertEqual(provider.calls, [])


if __name__ == '__main__':
    unittest.main()
