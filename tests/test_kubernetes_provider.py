import subprocess

import unittest

from ops_provider.kubernetes import KubernetesProvider


class FakeRunner:
    def __init__(self, stdout='{}'):
        self.stdout = stdout
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        return subprocess.CompletedProcess(args, 0, self.stdout, '')


class KubernetesProviderTests(unittest.TestCase):
  def test_namespace_is_fixed(self):
    with self.assertRaises(ValueError):
        KubernetesProvider('default')


  def test_resource_names_are_validated(self):
    provider = KubernetesProvider(runner=FakeRunner())
    with self.assertRaises(ValueError):
        provider.get_service_health('bad/name')
    with self.assertRaises(ValueError):
        provider.scale_service('frontend', 11)


  def test_health_and_logs_use_fixed_kubectl_operations(self):
    runner = FakeRunner('{"items": []}')
    provider = KubernetesProvider(runner=runner)
    assert provider.get_cluster_health()['healthy'] is False
    provider.get_logs('frontend', 20)
    assert runner.calls[1][:4] == ['kubectl', '-n', 'ops-sandbox', 'logs']


  def test_scale_is_a_real_deployment_operation(self):
    runner = FakeRunner('{"metadata":{"name":"frontend"}}')
    result = KubernetesProvider(runner=runner).scale_service('frontend', 2)
    assert result.changed is True
    self.assertIn('--replicas=2', runner.calls[0])


if __name__ == '__main__':
    unittest.main()
