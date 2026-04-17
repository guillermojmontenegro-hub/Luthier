from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.conflict_report import build_report
from core.models import EvaluationProfile


def _load_snapshot(path: Path) -> dict | None:
    if not path.is_file() or path.suffix.lower() != ".json":
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON snapshot: {path}") from exc

    if not {"schema_version", "skills", "summary"}.issubset(payload):
        return None
    return payload


def _report_for_input(path: Path, profile: EvaluationProfile, include_conflicts: bool) -> dict:
    snapshot = _load_snapshot(path)
    if snapshot is not None:
        return snapshot
    return build_report(path, profile, include_conflicts=include_conflicts).to_dict()


def _finding_identity(finding: dict) -> str:
    return (
        f"{finding.get('severity', 'unknown')}|"
        f"{finding.get('code', 'unknown')}|"
        f"{finding.get('source', 'static')}|"
        f"{finding.get('message', '')}"
    )


def _summarize_findings(findings: list[dict]) -> list[str]:
    summary = []
    for finding in sorted(findings, key=_finding_identity):
        summary.append(
            f"{finding.get('severity', 'unknown')}:{finding.get('code', 'unknown')}"
            f"[{finding.get('source', 'static')}]"
        )
    return summary


def _numeric_deltas(left: dict, right: dict) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key, left_value in left.items():
        right_value = right.get(key)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            delta = round(float(right_value) - float(left_value), 2)
            if delta != 0:
                deltas[key] = delta
    return deltas


def build_diff(
    left_path: Path,
    right_path: Path,
    profile: EvaluationProfile,
    include_conflicts: bool = True,
) -> dict:
    left_report = _report_for_input(left_path, profile, include_conflicts=include_conflicts)
    right_report = _report_for_input(right_path, profile, include_conflicts=include_conflicts)

    left_skills = {item["skill"]["name"]: item for item in left_report.get("skills", [])}
    right_skills = {item["skill"]["name"]: item for item in right_report.get("skills", [])}

    added_names = sorted(set(right_skills) - set(left_skills))
    removed_names = sorted(set(left_skills) - set(right_skills))
    common_names = sorted(set(left_skills) & set(right_skills))

    skill_diffs: list[dict] = []
    improved_skills = 0
    regressed_skills = 0
    changed_skills = 0

    for name in added_names:
        item = right_skills[name]
        skill_diffs.append(
            {
                "name": name,
                "status": "added",
                "risk_delta": round(item["scores"]["risk"], 2),
                "finding_count_delta": len(item["findings"]),
                "added_findings": _summarize_findings(item["findings"]),
                "removed_findings": [],
                "metric_deltas": item["metrics"],
                "score_deltas": item["scores"],
            }
        )

    for name in removed_names:
        item = left_skills[name]
        skill_diffs.append(
            {
                "name": name,
                "status": "removed",
                "risk_delta": round(-float(item["scores"]["risk"]), 2),
                "finding_count_delta": -len(item["findings"]),
                "added_findings": [],
                "removed_findings": _summarize_findings(item["findings"]),
                "metric_deltas": {key: -value for key, value in item["metrics"].items()},
                "score_deltas": {key: -value for key, value in item["scores"].items()},
            }
        )

    for name in common_names:
        left_item = left_skills[name]
        right_item = right_skills[name]
        left_findings = {_finding_identity(item): item for item in left_item["findings"]}
        right_findings = {_finding_identity(item): item for item in right_item["findings"]}
        added_findings = [
            right_findings[key] for key in sorted(set(right_findings) - set(left_findings))
        ]
        removed_findings = [
            left_findings[key] for key in sorted(set(left_findings) - set(right_findings))
        ]
        metric_deltas = _numeric_deltas(left_item["metrics"], right_item["metrics"])
        score_deltas = _numeric_deltas(left_item["scores"], right_item["scores"])
        risk_delta = round(
            float(right_item["scores"]["risk"]) - float(left_item["scores"]["risk"]),
            2,
        )
        finding_delta = len(right_item["findings"]) - len(left_item["findings"])

        changed = bool(added_findings or removed_findings or metric_deltas or score_deltas)
        if not changed:
            continue

        changed_skills += 1
        if risk_delta > 0:
            regressed_skills += 1
            status = "regressed"
        elif risk_delta < 0:
            improved_skills += 1
            status = "improved"
        else:
            status = "changed"

        skill_diffs.append(
            {
                "name": name,
                "status": status,
                "risk_delta": risk_delta,
                "finding_count_delta": finding_delta,
                "added_findings": _summarize_findings(added_findings),
                "removed_findings": _summarize_findings(removed_findings),
                "metric_deltas": metric_deltas,
                "score_deltas": score_deltas,
            }
        )

    skill_diffs.sort(key=lambda item: (item["status"], -abs(item["risk_delta"]), item["name"]))

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison": {
            "left": str(left_path),
            "right": str(right_path),
            "left_generated_at": left_report.get("generated_at"),
            "right_generated_at": right_report.get("generated_at"),
            "left_policy_pack": left_report.get("profile", {}).get("policy_pack"),
            "right_policy_pack": right_report.get("profile", {}).get("policy_pack"),
        },
        "summary": {
            "left_skill_count": len(left_skills),
            "right_skill_count": len(right_skills),
            "added_skills": len(added_names),
            "removed_skills": len(removed_names),
            "changed_skills": changed_skills,
            "improved_skills": improved_skills,
            "regressed_skills": regressed_skills,
            "left_conflict_count": len(left_report.get("conflicts", [])),
            "right_conflict_count": len(right_report.get("conflicts", [])),
            "conflict_delta": len(right_report.get("conflicts", []))
            - len(left_report.get("conflicts", [])),
        },
        "skills": skill_diffs,
    }
