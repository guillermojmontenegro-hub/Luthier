from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from adapters import create_adapter
from core.conflicts import analyze_conflicts
from core.discovery import discover_skills
from core.metrics import compute_metrics
from core.models import AuditedSkill, AuditReport, Conflict, EvaluationProfile, Finding
from core.policies import get_policy_prompt_version, get_policy_rules_version
from core.rules import evaluate_rules
from core.scoring import compute_scores
from prompts.structured import (
    build_report_synthesis_prompt_for_policy,
    build_skill_audit_prompt_for_policy,
    build_skill_compare_prompt_for_policy,
)


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
    llm_finding_count = 0
    llm_conflict_count = 0
    llm_summary = ""
    adapter = None
    if profile.llm_provider != "none":
        adapter = create_adapter(profile.llm_provider)

    for skill in discovered:
        metrics = compute_metrics(skill)
        findings = evaluate_rules(skill, metrics, profile)
        if adapter is not None:
            llm_result = adapter.evaluate(
                build_skill_audit_prompt_for_policy(skill, profile.policy_pack)
            )
            llm_findings = [
                Finding(
                    code=item.code,
                    severity=item.severity,
                    message=item.message,
                    evidence=item.evidence,
                    recommendation=item.recommendation,
                    source="llm",
                )
                for item in llm_result.findings
            ]
            findings.extend(llm_findings)
            llm_finding_count += len(llm_findings)
        scores = compute_scores(metrics, findings, skill, profile.policy_pack)
        audited.append(
            AuditedSkill(discovered=skill, metrics=metrics, findings=findings, scores=scores)
        )

    conflict_analysis = analyze_conflicts(discovered) if include_conflicts else None
    conflicts = conflict_analysis.conflicts if conflict_analysis is not None else []
    if include_conflicts and adapter is not None:
        skill_index = {skill.name: skill for skill in discovered}
        pair_names = (
            conflict_analysis.compared_skill_pairs
            if conflict_analysis is not None
            else [(left.name, right.name) for left, right in combinations(discovered, 2)]
        )
        for left_name, right_name in pair_names:
            left = skill_index[left_name]
            right = skill_index[right_name]
            llm_result = adapter.evaluate(
                build_skill_compare_prompt_for_policy(left, right, profile.policy_pack)
            )
            for item in llm_result.findings:
                priority = {"high": 320, "medium": 220, "low": 120}[item.severity]
                conflicts.append(
                    Conflict(
                        left_skill=left.name,
                        right_skill=right.name,
                        severity=item.severity,
                        category=item.code,
                        evidence=item.evidence,
                        priority=priority,
                        recommendation=item.recommendation,
                        source="llm",
                    )
                )
                llm_conflict_count += 1

    finding_count = sum(len(item.findings) for item in audited)
    avg_risk = round(sum(item.scores.risk for item in audited) / max(1, len(audited)), 2)
    highest_conflict_priority = max((item.priority for item in conflicts), default=0)
    if adapter is not None:
        llm_summary = adapter.evaluate(
            build_report_synthesis_prompt_for_policy(
                AuditReport(
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
                        "conflict_cluster_count": (
                            conflict_analysis.cluster_count if conflict_analysis is not None else 0
                        ),
                        "conflict_pairs_compared": (
                            conflict_analysis.compared_pairs if conflict_analysis is not None else 0
                        ),
                        "conflict_pairs_skipped": (
                            conflict_analysis.skipped_pairs if conflict_analysis is not None else 0
                        ),
                        "conflict_pairs_total": (
                            conflict_analysis.total_pairs if conflict_analysis is not None else 0
                        ),
                        "llm_provider": profile.llm_provider,
                        "llm_finding_count": llm_finding_count,
                        "llm_conflict_count": llm_conflict_count,
                    },
                ),
                profile.policy_pack,
            )
        ).summary

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
            "conflict_cluster_count": (
                conflict_analysis.cluster_count if conflict_analysis is not None else 0
            ),
            "conflict_pairs_compared": (
                conflict_analysis.compared_pairs if conflict_analysis is not None else 0
            ),
            "conflict_pairs_skipped": (
                conflict_analysis.skipped_pairs if conflict_analysis is not None else 0
            ),
            "conflict_pairs_total": (
                conflict_analysis.total_pairs if conflict_analysis is not None else 0
            ),
            "llm_provider": profile.llm_provider,
            "llm_finding_count": llm_finding_count,
            "llm_conflict_count": llm_conflict_count,
            "llm_summary": llm_summary,
            "requested_policy_pack": profile.requested_policy_pack,
            "policy_resolution": profile.policy_resolution,
            "policy_pack_version": profile.policy_pack,
            "rules_version": f"{profile.policy_pack}@{get_policy_rules_version(profile.policy_pack)}",
            "prompt_version": f"{profile.policy_pack}@{get_policy_prompt_version(profile.policy_pack)}",
        },
    )
