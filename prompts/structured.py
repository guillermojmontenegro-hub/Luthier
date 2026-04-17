from __future__ import annotations

from adapters.llm import StructuredPrompt
from core.models import AuditReport, DiscoveredSkill
from core.policies import get_policy_prompt_suffix, get_policy_prompt_version

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
    return build_skill_audit_prompt_for_policy(skill, "generic-agentic")


def build_skill_audit_prompt_for_policy(
    skill: DiscoveredSkill, policy_pack_name: str
) -> StructuredPrompt:
    suffix = get_policy_prompt_suffix(policy_pack_name, "skill-audit")
    instructions = SKILL_AUDIT_INSTRUCTIONS
    if suffix:
        instructions = f"{instructions} {suffix}"
    return StructuredPrompt(
        prompt_type="skill-audit",
        version=f"{policy_pack_name}@{get_policy_prompt_version(policy_pack_name)}",
        instructions=instructions,
        payload={
            "name": skill.name,
            "description": skill.description,
            "usage_lines": skill.usage_lines,
            "restriction_lines": skill.restriction_lines,
            "examples": skill.examples,
            "sections": skill.sections,
            "content": skill.content,
            "policy_pack": policy_pack_name,
            "prompt_version": get_policy_prompt_version(policy_pack_name),
        },
    )


def build_skill_compare_prompt(left: DiscoveredSkill, right: DiscoveredSkill) -> StructuredPrompt:
    return build_skill_compare_prompt_for_policy(left, right, "generic-agentic")


def build_skill_compare_prompt_for_policy(
    left: DiscoveredSkill, right: DiscoveredSkill, policy_pack_name: str
) -> StructuredPrompt:
    suffix = get_policy_prompt_suffix(policy_pack_name, "skill-compare")
    instructions = SKILL_COMPARE_INSTRUCTIONS
    if suffix:
        instructions = f"{instructions} {suffix}"
    return StructuredPrompt(
        prompt_type="skill-compare",
        version=f"{policy_pack_name}@{get_policy_prompt_version(policy_pack_name)}",
        instructions=instructions,
        payload={
            "left_skill": left.name,
            "left_description": left.description,
            "left_sections": left.sections,
            "right_skill": right.name,
            "right_description": right.description,
            "right_sections": right.sections,
            "policy_pack": policy_pack_name,
            "prompt_version": get_policy_prompt_version(policy_pack_name),
        },
    )


def build_report_synthesis_prompt(report: AuditReport) -> StructuredPrompt:
    return build_report_synthesis_prompt_for_policy(report, "generic-agentic")


def build_report_synthesis_prompt_for_policy(
    report: AuditReport, policy_pack_name: str
) -> StructuredPrompt:
    suffix = get_policy_prompt_suffix(policy_pack_name, "report-synthesis")
    instructions = REPORT_SYNTHESIS_INSTRUCTIONS
    if suffix:
        instructions = f"{instructions} {suffix}"
    return StructuredPrompt(
        prompt_type="report-synthesis",
        version=f"{policy_pack_name}@{get_policy_prompt_version(policy_pack_name)}",
        instructions=instructions,
        payload={
            "schema_version": report.schema_version,
            "skill_count": len(report.skills),
            "finding_count": report.summary.get("finding_count", 0),
            "conflict_count": report.summary.get("conflict_count", 0),
            "average_risk": report.summary.get("average_risk", 0),
            "policy_pack": policy_pack_name,
            "prompt_version": get_policy_prompt_version(policy_pack_name),
        },
    )
