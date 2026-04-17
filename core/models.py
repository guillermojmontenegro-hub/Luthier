from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class EvaluationProfile:
    version: str
    name: str
    root_path: str
    output_formats: list[str]
    language: str
    shell: str
    operating_system: str
    network_access: str
    approval_mode: str
    runtime_agnostic: bool
    requested_policy_pack: str
    policy_pack: str
    policy_resolution: str
    agent_runtime: str
    model_family: str
    llm_provider: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class FileReference:
    path: str
    exists: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class DiscoveredSkill:
    name: str
    root_path: str
    main_file: str
    source_files: list[str]
    description: str
    usage_lines: list[str]
    restriction_lines: list[str]
    examples: list[str]
    auxiliary_files: list[str]
    scripts: list[str]
    references: list[FileReference]
    platform_signals: list[str]
    language_mix: dict[str, int]
    content: str
    sections: list[str]
    total_size_bytes: int

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["references"] = [item.to_dict() for item in self.references]
        return payload


@dataclass(slots=True)
class SkillMetrics:
    description_chars: int
    description_tokens_estimate: int
    total_chars: int
    total_tokens_estimate: int
    section_count: int
    imperative_steps: int
    restriction_count: int
    example_count: int
    tool_reference_count: int
    non_operational_ratio: float
    instruction_density: float
    context_cost_score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Finding:
    code: str
    severity: str
    message: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    source: str = "static"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Conflict:
    left_skill: str
    right_skill: str
    severity: str
    category: str
    evidence: list[str]
    priority: int = 0
    recommendation: str = ""
    source: str = "static"
    cluster_id: str | None = None
    cluster_size: int = 0
    comparison_context: str = "full-scan"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ConflictDetectionResult:
    conflicts: list[Conflict]
    cluster_count: int
    compared_pairs: int
    skipped_pairs: int
    total_pairs: int
    compared_skill_pairs: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conflicts": [item.to_dict() for item in self.conflicts],
            "cluster_count": self.cluster_count,
            "compared_pairs": self.compared_pairs,
            "skipped_pairs": self.skipped_pairs,
            "total_pairs": self.total_pairs,
        }


@dataclass(slots=True)
class ScoreCard:
    discoverability: float
    specificity: float
    portability: float
    maintainability: float
    risk: float
    context_cost: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class AuditedSkill:
    discovered: DiscoveredSkill
    metrics: SkillMetrics
    findings: list[Finding]
    scores: ScoreCard

    def to_dict(self) -> dict:
        return {
            "skill": self.discovered.to_dict(),
            "metrics": self.metrics.to_dict(),
            "findings": [item.to_dict() for item in self.findings],
            "scores": self.scores.to_dict(),
        }


@dataclass(slots=True)
class AuditReport:
    schema_version: str
    generated_at: str
    profile: EvaluationProfile
    skills: list[AuditedSkill]
    conflicts: list[Conflict]
    summary: dict[str, int | float]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "profile": self.profile.to_dict(),
            "skills": [item.to_dict() for item in self.skills],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "summary": self.summary,
        }
