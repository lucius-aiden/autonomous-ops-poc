"""Hosted Gemini reasoning adapter.

This module only translates a bounded investigation brief to/from Gemini. It
does not expose tools, credentials, or infrastructure handles to the model.
"""

import json
import os
import time
import urllib.error
import urllib.request

from .reasoning import InvalidDecision, OperationalDecision, build_prompt


class GeminiReasoningError(RuntimeError):
    """A transport or provider-level failure; callers must fail closed."""


class GeminiReasoningProvider:
    def __init__(self, model: str | None = None, api_key: str | None = None, timeout: float = 90.0, retry_delays: tuple[float, ...] = (10, 30, 60)):
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.timeout = timeout
        self.retry_delays = retry_delays
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for live reasoning")

    def decide(self, investigation: dict) -> OperationalDecision:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        schema = {
            "type": "OBJECT",
            "properties": {
                "decision": {"type": "STRING", "enum": ["OBSERVE", "ACT", "ESCALATE"]},
                "summary": {"type": "STRING"}, "diagnosis": {"type": "STRING"},
                "confidence": {"type": "NUMBER"},
                "requested_action": {"type": "STRING", "nullable": True},
                "target": {"type": "STRING", "nullable": True},
                "parameters": {"type": "OBJECT"}, "reason": {"type": "STRING"},
                "verification_plan": {"type": "STRING"},
            },
            "required": ["decision", "summary", "diagnosis", "confidence", "requested_action", "target", "parameters", "reason", "verification_plan"],
        }
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": build_prompt(investigation)}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema},
        }).encode()
        request = urllib.request.Request(
            endpoint + "?key=" + self.api_key,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        for attempt in range(len(self.retry_delays) + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as error:
                # Retry only transient service unavailability; never retry auth,
                # schema, quota, or client errors, and never expose the URL/body.
                if error.code != 503 or attempt >= len(self.retry_delays):
                    raise GeminiReasoningError(f"Gemini request failed: HTTP {error.code}") from None
                time.sleep(self.retry_delays[attempt])
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
                raise GeminiReasoningError(f"Gemini request failed: {type(error).__name__}") from None
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            value = json.loads(text)
            return OperationalDecision.from_dict(value)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise InvalidDecision("Gemini response was not a valid JSON decision") from error
