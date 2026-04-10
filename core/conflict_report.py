from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.conflicts import detect_conflicts
from core.discovery import discover_skills
from core.metrics import compute_metrics
from core.models import AuditedSkill, AuditReport, EvaluationProfile
from core.rules import evaluate_rules
from core.scoring import compute_scores


def _matches_folder_selector(skill_root: Path, base_path: Path, selectors: set[str]) -> bool:
    normalized_selectors = {
        selector.strip().strip("/").replace("\\", "/") for selector in selectors if selector.strip()
    }
    if not normalized_selectors:
        return True

    try:
        relative_root = skill_root.resolve().relative_to(base_path.resolve())
        relative_text = relative_root.as_posix()
        relative_parts = set(relative_root.parts)
    except ValueError:
        relative_text = skill_root.name
        relative_parts = {skill_root.name}

    for selector in normalized_selectors:
        if selector == relative_text:
            return True
        if relative_text.startswith(f"{selector}/"):
            return True
        if selector in relative_parts:
            return True
    return False


def build_report(
    path: Path,
    profile: EvaluationProfile,
    include_conflicts: bool = False,
    selected_skills: set[str] | None = None,
    selected_folders: set[str] | None = None,
) -> AuditReport:
    resolved_path = path.resolve()
    scope_root = resolved_path if resolved_path.is_dir() else resolved_path.parent
    discovered = discover_skills(path)
    if selected_skills:
        discovered = [skill for skill in discovered if skill.name in selected_skills]
    if selected_folders:
        discovered = [
            skill
            for skill in discovered
            if _matches_folder_selector(Path(skill.root_path), scope_root, selected_folders)
        ]

    audited: list[AuditedSkill] = []
    for skill in discovered:
        metrics = compute_metrics(skill)
        findings = evaluate_rules(skill, metrics, profile)
        scores = compute_scores(metrics, findings)
        audited.append(
            AuditedSkill(discovered=skill, metrics=metrics, findings=findings, scores=scores)
        )

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
