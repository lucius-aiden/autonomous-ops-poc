import json
import unittest
from unittest.mock import patch

from ops_provider.groq import DECISION_SCHEMA, GroqReasoningProvider
from ops_provider.reasoning import InvalidDecision


def _decision(**overrides):
    value = {"decision": "OBSERVE", "summary": "recovering", "diagnosis": "self healing", "confidence": 0.8, "requested_action": None, "target": None, "parameters": {"replicas": None, "context": None}, "reason": "least disruptive", "verification_plan": "observe"}
    value.update(overrides)
    return value


class GroqSchemaTests(unittest.TestCase):
    def _provider_result(self, value):
        provider = GroqReasoningProvider(api_key="test", response_mode="json_object", timeout=1)
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with patch("urllib.request.urlopen", return_value=Reply()), patch("json.load", return_value={"choices": [{"message": {"content": json.dumps(value)}}]}):
            return provider.decide({})

    def test_every_object_is_closed_and_all_properties_required(self):
        def walk(schema):
            if schema.get("type") == "object":
                self.assertFalse(schema.get("additionalProperties", True))
                self.assertEqual(set(schema.get("properties", {})), set(schema.get("required", [])))
                for child in schema.get("properties", {}).values(): walk(child)
            for child in schema.get("anyOf", []): walk(child)
        walk(DECISION_SCHEMA)

    def test_semantic_decisions_accept_nullable_wire_parameters(self):
        for value in (_decision(), _decision(decision="ESCALATE"), _decision(decision="ACT", requested_action="service.restart", target="frontend", parameters={"replicas": None, "context": None}), _decision(decision="ACT", requested_action="service.scale", target="frontend", parameters={"replicas": 2, "context": None})):
            value["parameters"] = {key: item for key, item in value["parameters"].items() if item is not None}
            self.assertIsNotNone(value)

    def test_inappropriate_parameter_combinations_stay_rejected(self):
        with self.assertRaises(InvalidDecision):
            from ops_provider.reasoning import OperationalDecision
            OperationalDecision.from_dict(_decision(decision="ACT", requested_action="service.restart", target="frontend", parameters={"replicas": 2}))
        with self.assertRaises(InvalidDecision):
            from ops_provider.reasoning import OperationalDecision
            OperationalDecision.from_dict(_decision(decision="OBSERVE", parameters={"replicas": 2, "context": None}))

    def test_malformed_output_is_rejected(self):
        provider = GroqReasoningProvider(api_key="test", timeout=1)
        response = {"choices": [{"message": {"content": json.dumps({"decision": "ACT"})}}]}
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        Reply.read = lambda self, *args: b""
        with patch("urllib.request.urlopen", return_value=Reply()), patch("json.load", return_value=response):
            with self.assertRaises(InvalidDecision): provider.decide({})

    def test_json_object_observe_can_omit_irrelevant_parameters(self):
        result = self._provider_result(_decision(parameters=None))
        self.assertEqual(result.decision, "OBSERVE")

    def test_json_object_rejects_missing_act_action(self):
        value = _decision(decision="ACT", target="frontend", parameters={})
        value.pop("requested_action")
        with self.assertRaises(InvalidDecision): self._provider_result(value)

    def test_json_object_rejects_missing_act_target(self):
        value = _decision(decision="ACT", requested_action="service.restart", parameters={})
        value.pop("target")
        with self.assertRaises(InvalidDecision): self._provider_result(value)

    def test_json_object_rejects_missing_scale_replicas(self):
        value = _decision(decision="ACT", requested_action="service.scale", target="frontend", parameters={})
        with self.assertRaises(InvalidDecision): self._provider_result(value)

    def test_json_object_rejects_extra_consequential_values(self):
        value = _decision(parameters={"replicas": 2, "context": None})
        with self.assertRaises(InvalidDecision): self._provider_result(value)

    def _turn_result(self, value):
        provider = GroqReasoningProvider(api_key="test", response_mode="json_object", timeout=1)
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with patch("urllib.request.urlopen", return_value=Reply()), patch("json.load", return_value={"choices": [{"message": {"content": json.dumps(value)}}]}):
            return provider.decide_turn({"initial_observation": {}, "tool_results": []})

    def test_interactive_read_tools_are_accepted(self):
        for tool, arguments in (("inspect_service", {"service": "frontend"}), ("get_service_health", {"service": "frontend"}), ("get_pods", {"service": "frontend"}), ("get_logs", {"service": "frontend", "tail_lines": 20})):
            self.assertEqual(self._turn_result({"type": "tool", "tool": tool, "arguments": arguments})["tool"], tool)

    def test_interactive_final_decisions_are_accepted(self):
        for kind in ("OBSERVE", "ESCALATE", "ACT"):
            value = _decision(decision=kind)
            if kind == "ACT": value.update(requested_action="service.restart", target="frontend", parameters={})
            self.assertEqual(self._turn_result({"type": "final", "decision": value})["decision"]["decision"], kind)

    def test_interactive_rejects_unknown_or_malformed_tools(self):
        with self.assertRaises(InvalidDecision): self._turn_result({"type": "tool", "tool": "kubectl", "arguments": {"service": "frontend"}})
        with self.assertRaises(InvalidDecision): self._turn_result({"type": "tool", "tool": "get_logs", "arguments": {"service": "frontend", "tail_lines": "many"}})
        with self.assertRaises(InvalidDecision): self._turn_result({"type": "wat"})


if __name__ == "__main__": unittest.main()
