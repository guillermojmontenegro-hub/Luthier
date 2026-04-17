from __future__ import annotations

from core.models import DiscoveredSkill, Finding, ScoreCard, SkillMetrics
from core.policies import get_policy_pack

SEVERITY_WEIGHT = {"low": 0.8, "medium": 1.5, "high": 2.5}


def _count_pattern_hits(content: str, patterns: list[str], max_hits: int) -> int:
    lowered = content.lower()
    hits = 0
    for pattern in patterns:
        if pattern.lower() in lowered:
            hits += 1
        if hits >= max_hits:
            return max_hits
    return hits


def _apply_policy_adjustments(
    scores: dict[str, float],
    *,
    skill: DiscoveredSkill,
    findings: list[Finding],
    policy_pack_name: str,
) -> dict[str, float]:
    policy = get_policy_pack(policy_pack_name)
    scoring = policy.get("scoring", {})
    if not scoring:
        return scores

    positive_hits = _count_pattern_hits(
        skill.content,
        scoring.get("positive_patterns", []),
        scoring.get("max_positive_hits", 0),
    )
    negative_hits = _count_pattern_hits(
        skill.content,
        scoring.get("negative_patterns", []),
        scoring.get("max_negative_hits", 0),
    )
    negative_codes = set(scoring.get("negative_finding_codes", []))
    negative_hits += sum(1 for item in findings if item.code in negative_codes)
    negative_hits = min(negative_hits, scoring.get("max_negative_hits", negative_hits))

    for key, value in scoring.get("positive_effects", {}).items():
        scores[key] = scores.get(key, 0.0) + positive_hits * float(value)
    for key, value in scoring.get("negative_effects", {}).items():
        scores[key] = scores.get(key, 0.0) + negative_hits * float(value)

    return scores


def compute_scores(
    metrics: SkillMetrics,
    findings: list[Finding],
    skill: DiscoveredSkill,
    policy_pack_name: str,
) -> ScoreCard:
    risk = min(10.0, round(sum(SEVERITY_WEIGHT[item.severity] for item in findings), 2))
    discoverability = 10.0
    if metrics.description_tokens_estimate > 80:
        discoverability -= 2.0
    if metrics.description_tokens_estimate < 6:
        discoverability -= 3.0
    discoverability -= min(3.0, metrics.non_operational_ratio * 4)

    specificity = min(
        10.0, max(0.0, round(metrics.instruction_density * 220 + metrics.example_count * 0.8, 2))
    )
    portability = 10.0 - min(6.0, metrics.tool_reference_count * 0.2)
    maintainability = 10.0 - min(
        6.0, metrics.restriction_count * 0.35 + metrics.section_count * 0.1
    )
    context_cost = min(10.0, metrics.context_cost_score)
    adjusted = _apply_policy_adjustments(
        {
            "discoverability": discoverability,
            "specificity": specificity,
            "portability": portability,
            "maintainability": maintainability,
            "risk": risk,
            "context_cost": context_cost,
        },
        skill=skill,
        findings=findings,
        policy_pack_name=policy_pack_name,
    )

    return ScoreCard(
        discoverability=round(max(0.0, min(10.0, adjusted["discoverability"])), 2),
        specificity=round(max(0.0, min(10.0, adjusted["specificity"])), 2),
        portability=round(max(0.0, min(10.0, adjusted["portability"])), 2),
        maintainability=round(max(0.0, min(10.0, adjusted["maintainability"])), 2),
        risk=round(max(0.0, min(10.0, adjusted["risk"])), 2),
        context_cost=round(max(0.0, min(10.0, adjusted["context_cost"])), 2),
    )
