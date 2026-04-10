from __future__ import annotations

from pathlib import Path

from core.conflict_report import build_report
from core.models import AuditReport, EvaluationProfile


def audit_path(path: Path, profile: EvaluationProfile) -> AuditReport:
    return build_report(path, profile, include_conflicts=False)
