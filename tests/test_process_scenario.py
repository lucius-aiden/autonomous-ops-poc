import unittest

from ops_provider.agent_tools import ReadOnlyToolRegistry
from ops_provider.models import ServiceObservation
from ops_provider.scenarios import ProcessLocalWedgeScenario


class FakeProvider:
    namespace = "ops-sandbox"
    def __init__(self): self.calls = []
    def observe_service(self, service):
        return ServiceObservation.now(service, desired_replicas=1, ready_replicas=1, available_replicas=1, pods=[{"name": "p1", "phase": "Running", "ready": True}], warnings=[], logs="")
    def get_pods(self, service): return [{"name": "p1", "phase": "Running", "ready": True}]
    def _runner(self, args, **kwargs):
        self.calls.append(args)
        class Result:
            returncode = 0
            stdout = "200\n"
            stderr = ""
        return Result()
    def _run(self, args, **kwargs): self.calls.append(args); return "{}"


class ProcessScenarioTests(unittest.TestCase):
    def test_setup_and_cleanup_use_current_pod_and_no_agent_tool(self):
        provider = FakeProvider(); scenario = ProcessLocalWedgeScenario(provider)
        baseline = scenario.setup(); self.assertEqual(baseline["pod"], "p1")
        self.assertEqual(scenario.inject()["fault"], "process_local_runtime_wedged")
        self.assertTrue(scenario.cleanup()["cleaned"])
        self.assertTrue(any("__test__/wedge" in " ".join(call) for call in provider.calls))
        self.assertNotIn("__test__/wedge", ReadOnlyToolRegistry.TOOLS)


if __name__ == "__main__": unittest.main()
