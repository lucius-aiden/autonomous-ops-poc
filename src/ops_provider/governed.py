"""Application-facing write boundary: authorize first, execute second."""

import json
import os
import subprocess
from dataclasses import asdict
from typing import Callable

from .interface import OperationsProvider
from .models import OperationResult


class GovernanceDenied(RuntimeError):
    def __init__(self, decision: dict):
        self.decision = decision
        super().__init__(f"MetaMynd did not permit operation: {decision.get('decision')}")


class MetaMyndAuthorizer:
    """Calls the official Node SDK adapter; transport errors fail closed."""

    def __init__(self, runner: Callable = subprocess.run, node: str | None = None, adapter: str | None = None):
        self.runner = runner
        self.node = node or os.environ.get('METAMYND_NODE', 'node')
        self.adapter = adapter or os.environ.get('METAMYND_ADAPTER', './metamynd/authorize.mjs')

    def authorize(self, action: str, resource: str) -> dict:
        request = json.dumps({'action': action, 'resource': resource, 'context': {'source': 'autonomous-ops-poc'}})
        completed = self.runner([self.node, self.adapter], input=request, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise GovernanceDenied({'decision': 'block', 'reason': 'MetaMynd adapter unavailable'})
        try:
            verdict = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as error:
            raise GovernanceDenied({'decision': 'block', 'reason': 'malformed MetaMynd verdict'}) from error
        if verdict.get('decision') not in {'allow', 'observe', 'block', 'escalate'}:
            raise GovernanceDenied({'decision': 'block', 'reason': 'unknown MetaMynd verdict'})
        return verdict


class GovernedOperations:
    def __init__(self, provider: OperationsProvider, authorizer: MetaMyndAuthorizer):
        self.provider = provider
        self.authorizer = authorizer

    def _authorize(self, action: str, resource: str) -> dict:
        verdict = self.authorizer.authorize(action, resource)
        if verdict['decision'] not in {'allow', 'observe'}:
            raise GovernanceDenied(verdict)
        return verdict

    def restart_service(self, service: str) -> dict:
        verdict = self._authorize('service.restart', service)
        result = self.provider.restart_service(service)
        return {'authorization': verdict, 'operation': asdict(result)}

    def scale_service(self, service: str, replicas: int) -> dict:
        verdict = self._authorize('service.scale', service)
        result = self.provider.scale_service(service, replicas)
        return {'authorization': verdict, 'operation': asdict(result)}
