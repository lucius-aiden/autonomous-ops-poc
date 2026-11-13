from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario_id: str
    detected: bool
    incident_opened: bool
    evidence_collected: bool
    recovered: bool
    detection_latency_seconds: float | None
    recovery_latency_seconds: float | None
    unexpected_mutation: bool


def evaluate(scenario_id: str, started_at: datetime, detected_at: datetime | None, incident_opened: bool, evidence_collected: bool, recovered_at: datetime | None, unexpected_mutation: bool = False) -> ScenarioEvaluation:
    return ScenarioEvaluation(scenario_id, detected_at is not None, incident_opened, evidence_collected, recovered_at is not None, (detected_at - started_at).total_seconds() if detected_at else None, (recovered_at - started_at).total_seconds() if recovered_at else None, unexpected_mutation)
