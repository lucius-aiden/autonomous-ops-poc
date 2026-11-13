import json
import subprocess
import unittest

from ops_provider.governed import GovernedOperations, GovernanceDenied, MetaMyndAuthorizer
from ops_provider.models import OperationResult


class FakeProvider:
    def __init__(self):
        self.calls = []

    def restart_service(self, service):
        self.calls.append(('restart', service))
        return OperationResult('restart_service', service, 'ops-sandbox', True, {})

    def scale_service(self, service, replicas):
        self.calls.append(('scale', service, replicas))
        return OperationResult('scale_service', service, 'ops-sandbox', True, {})


class FakeAuthorizer:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def authorize(self, action, resource):
        self.calls.append((action, resource))
        return self.decision


class GovernedOperationsTests(unittest.TestCase):
    def test_block_never_reaches_provider(self):
        provider = FakeProvider()
        service = GovernedOperations(provider, FakeAuthorizer({'decision': 'block'}))
        with self.assertRaises(GovernanceDenied):
            service.restart_service('frontend')
        self.assertEqual(provider.calls, [])

    def test_escalate_never_reaches_provider(self):
        provider = FakeProvider()
        service = GovernedOperations(provider, FakeAuthorizer({'decision': 'escalate', 'escalationId': 'e1'}))
        with self.assertRaises(GovernanceDenied):
            service.scale_service('frontend', 2)
        self.assertEqual(provider.calls, [])

    def test_allow_reaches_provider_and_preserves_evidence(self):
        provider = FakeProvider()
        verdict = {'decision': 'allow', 'authorizationId': 'a1', 'agentDid': 'did:test:agent'}
        result = GovernedOperations(provider, FakeAuthorizer(verdict)).restart_service('frontend')
        self.assertEqual(result['authorization'], verdict)
        self.assertEqual(provider.calls, [('restart', 'frontend')])

    def test_transport_failure_fails_closed(self):
        def failed(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, '', 'network down')
        authorizer = MetaMyndAuthorizer(runner=failed)
        with self.assertRaises(GovernanceDenied):
            authorizer.authorize('service.restart', 'frontend')

    def test_malformed_and_unknown_verdicts_fail_closed(self):
        for output in ('not json', json.dumps({'decision': 'maybe'})):
            def runner(*args, _output=output, **kwargs):
                return subprocess.CompletedProcess(args[0], 0, _output, '')
            with self.assertRaises(GovernanceDenied):
                MetaMyndAuthorizer(runner=runner).authorize('service.restart', 'frontend')


if __name__ == '__main__':
    unittest.main()
