"""Groq hosted reasoning adapter using strict JSON Schema structured output."""

import json
import os
import urllib.error
import urllib.request

from .reasoning import InvalidDecision, OperationalDecision, build_prompt


class GroqReasoningError(RuntimeError):
    """A provider/transport failure; callers must fail closed."""


DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["OBSERVE", "ACT", "ESCALATE"]},
        "summary": {"type": "string"}, "diagnosis": {"type": "string"},
        "confidence": {"type": "number"},
        "requested_action": {"type": ["string", "null"]},
        "target": {"type": ["string", "null"]},
        "parameters": {"type": "object", "additionalProperties": False, "properties": {
            "replicas": {"type": ["integer", "null"], "minimum": 0, "maximum": 10},
            "context": {"type": ["object", "null"], "additionalProperties": False, "properties": {"riskLevel": {"type": "string", "enum": ["low", "medium", "high", "critical"]}}, "required": ["riskLevel"]},
        }, "required": ["replicas", "context"]}, "reason": {"type": "string"},
        "verification_plan": {"type": "string"},
    },
    "required": ["decision", "summary", "diagnosis", "confidence", "requested_action", "target", "parameters", "reason", "verification_plan"],
}


class GroqReasoningProvider:
    def __init__(self, model: str = "openai/gpt-oss-20b", api_key: str | None = None, endpoint: str = "https://api.groq.com/openai/v1/chat/completions", timeout: float = 60.0):
        self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.endpoint, self.timeout = endpoint, timeout
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is required for live reasoning")

    def decide(self, investigation: dict) -> OperationalDecision:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": build_prompt(investigation)}],
            "temperature": 0,
            "response_format": {"type": "json_schema", "json_schema": {"name": "operational_decision", "strict": True, "schema": DECISION_SCHEMA}},
        }).encode()
        request = urllib.request.Request(self.endpoint, data=body, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "autonomous-ops-poc/2.0 (https://github.com/lucius-aiden/autonomous-ops-poc)"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read(400).decode("utf-8", errors="replace")
            raise GroqReasoningError(f"Groq request failed: HTTP {error.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise GroqReasoningError(f"Groq request failed: {type(error).__name__}") from None
        try:
            text = payload["choices"][0]["message"]["content"]
            value = json.loads(text)
            # Strict schemas require both parameter keys; remove inactive nulls
            # before applying the existing bounded OperationalDecision validator.
            params = value.get("parameters", {})
            if isinstance(params, dict):
                value["parameters"] = {key: item for key, item in params.items() if item is not None}
            return OperationalDecision.from_dict(value)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise InvalidDecision("Groq response was not a valid JSON decision") from error
