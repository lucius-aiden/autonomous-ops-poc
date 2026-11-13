from dataclasses import asdict

from .governed import GovernedOperations, GovernanceDenied
from .health import classify
from .investigation import build_investigation
from .kubernetes import KubernetesProvider
from .reasoning import OperationalDecision, ReasoningProvider


class BoundedAgentLoop:
    def __init__(self, reasoning: ReasoningProvider, provider: KubernetesProvider, governed: GovernedOperations):
        self.reasoning, self.provider, self.governed = reasoning, provider, governed

    def handle(self, investigation: dict) -> dict:
        decision = self.reasoning.decide(investigation)
        if not isinstance(decision, OperationalDecision):
            raise TypeError("reasoning provider must return OperationalDecision")
        result = {"decision": asdict(decision), "governance": None, "execution": None, "verification": None}
        if decision.decision != "ACT":
            return result
        try:
            if decision.requested_action == "service.restart":
                execution = self.governed.restart_service(decision.target, decision.parameters.get("context"))
            elif decision.requested_action == "service.scale":
                execution = self.governed.scale_service(decision.target, decision.parameters["replicas"], decision.parameters.get("context"))
            else:
                raise RuntimeError("unsupported action reached execution")
            result["governance"] = execution["authorization"]
            result["execution"] = execution["operation"]
            observation = self.provider.observe_service(decision.target)
            result["verification"] = {"health": classify(observation).value, "observation": observation.__dict__}
        except GovernanceDenied as denied:
            result["governance"] = denied.decision
        return result
