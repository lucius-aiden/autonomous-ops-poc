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


if __name__ == "__main__": unittest.main()
