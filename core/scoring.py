from __future__ import annotations

from core.models import Finding, ScoreCard, SkillMetrics


SEVERITY_WEIGHT = {"low": 0.8, "medium": 1.5, "high": 2.5}


def compute_scores(metrics: SkillMetrics, findings: list[Finding]) -> ScoreCard:
    risk = min(10.0, round(sum(SEVERITY_WEIGHT[item.severity] for item in findings), 2))
    discoverability = 10.0
    if metrics.description_tokens_estimate > 80:
        discoverability -= 2.0
    if metrics.description_tokens_estimate < 6:
        discoverability -= 3.0
    discoverability -= min(3.0, metrics.non_operational_ratio * 4)

    specificity = min(10.0, max(0.0, round(metrics.instruction_density * 220 + metrics.example_count * 0.8, 2)))
    portability = 10.0 - min(6.0, metrics.tool_reference_count * 0.2)
    maintainability = 10.0 - min(6.0, metrics.restriction_count * 0.35 + metrics.section_count * 0.1)
    context_cost = min(10.0, metrics.context_cost_score)

    return ScoreCard(
        discoverability=round(max(0.0, discoverability), 2),
        specificity=round(specificity, 2),
        portability=round(max(0.0, portability), 2),
        maintainability=round(max(0.0, maintainability), 2),
        risk=risk,
        context_cost=context_cost,
    )
