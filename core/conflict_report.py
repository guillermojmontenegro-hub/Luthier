from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.conflicts import detect_conflicts
from core.discovery import discover_skills
from core.metrics import compute_metrics
from core.models import AuditReport, AuditedSkill, EvaluationProfile
from core.rules import evaluate_rules
from core.scoring import compute_scores


def build_report(
    path: Path,
    profile: EvaluationProfile,
    include_conflicts: bool = False,
    selected_skills: set[str] | None = None,
) -> AuditReport:
    discovered = discover_skills(path)
    if selected_skills:
        discovered = [skill for skill in discovered if skill.name in selected_skills]

    audited: list[AuditedSkill] = []
    for skill in discovered:
        metrics = compute_metrics(skill)
        findings = evaluate_rules(skill, metrics, profile)
        scores = compute_scores(metrics, findings)
        audited.append(AuditedSkill(discovered=skill, metrics=metrics, findings=findings, scores=scores))

    conflicts = detect_conflicts(discovered) if include_conflicts else []
    finding_count = sum(len(item.findings) for item in audited)
    avg_risk = round(sum(item.scores.risk for item in audited) / max(1, len(audited)), 2)
    highest_conflict_priority = max((item.priority for item in conflicts), default=0)
    return AuditReport(
        schema_version="1.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        profile=profile,
        skills=audited,
        conflicts=conflicts,
        summary={
            "skill_count": len(audited),
            "finding_count": finding_count,
            "conflict_count": len(conflicts),
            "average_risk": avg_risk,
            "highest_conflict_priority": highest_conflict_priority,
        },
    )
