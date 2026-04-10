from __future__ import annotations

from adapters.llm import StructuredPrompt
from core.models import AuditReport, DiscoveredSkill

PROMPT_VERSION = "1.0"

SKILL_AUDIT_INSTRUCTIONS = (
    "Audit one skill and return a structured JSON object with findings, severity, "
    "explicit evidence, and a concise summary."
)
SKILL_COMPARE_INSTRUCTIONS = (
    "Compare two skills and return structured overlap or conflict findings with "
    "evidence and a concise summary."
)
REPORT_SYNTHESIS_INSTRUCTIONS = (
    "Summarize an audit report into a concise structured response without "
    "inventing new metrics."
)


def build_skill_audit_prompt(skill: DiscoveredSkill) -> StructuredPrompt:
    return StructuredPrompt(
        prompt_type="skill-audit",
        version=PROMPT_VERSION,
        instructions=SKILL_AUDIT_INSTRUCTIONS,
        payload={
            "name": skill.name,
            "description": skill.description,
            "usage_lines": skill.usage_lines,
            "restriction_lines": skill.restriction_lines,
            "examples": skill.examples,
            "sections": skill.sections,
            "content": skill.content,
        },
    )


def build_skill_compare_prompt(left: DiscoveredSkill, right: DiscoveredSkill) -> StructuredPrompt:
    return StructuredPrompt(
        prompt_type="skill-compare",
        version=PROMPT_VERSION,
        instructions=SKILL_COMPARE_INSTRUCTIONS,
        payload={
            "left_skill": left.name,
            "left_description": left.description,
            "left_sections": left.sections,
            "right_skill": right.name,
            "right_description": right.description,
            "right_sections": right.sections,
        },
    )


def build_report_synthesis_prompt(report: AuditReport) -> StructuredPrompt:
    return StructuredPrompt(
        prompt_type="report-synthesis",
        version=PROMPT_VERSION,
        instructions=REPORT_SYNTHESIS_INSTRUCTIONS,
        payload={
            "schema_version": report.schema_version,
            "skill_count": len(report.skills),
            "finding_count": report.summary.get("finding_count", 0),
            "conflict_count": report.summary.get("conflict_count", 0),
            "average_risk": report.summary.get("average_risk", 0),
        },
    )
