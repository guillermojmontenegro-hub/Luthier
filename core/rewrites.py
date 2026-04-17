from __future__ import annotations

from core.models import DiscoveredSkill, Finding

REWRITE_ACTIONS = {
    "description-too-long": "Condense the description to one or two lines with a narrower trigger.",
    "description-too-vague": (
        "Replace generic wording with a concrete trigger, scope, and expected outcome."
    ),
    "over-specified-workflow": "Keep only the decisive steps and move optional detail to examples.",
    "rigid-tooling-or-sequence": (
        "Relax mandatory sequencing unless the tool or order is truly required."
    ),
    "duplicated-instructions": "Merge repeated instructions into one canonical rule.",
    "broken-references": "Fix or remove file references that no longer resolve.",
    "language-mix": (
        "Rewrite the skill in a single dominant language unless bilingual output is required."
    ),
    "excessive-constraints": "Convert some hard constraints into softer guidance to improve reuse.",
    "low-signal-context-balance": "Trim narrative context and keep the operational instructions.",
    "non-canonical-skill-name": "Rename the skill folder using lowercase snake_case.",
    "non-canonical-auxiliary-name": "Rename helper files using lowercase snake_case basenames.",
}


def _description_trigger(skill: DiscoveredSkill) -> str:
    if skill.usage_lines:
        return skill.usage_lines[0].rstrip(".")
    if skill.sections:
        return f"the workflow matches the skill's `{skill.sections[0]}` section"
    return "the repository task matches this skill's intended scope"


def _description_scope(skill: DiscoveredSkill) -> str:
    if skill.restriction_lines:
        return skill.restriction_lines[0].rstrip(".")
    if skill.examples:
        return f"following patterns such as {skill.examples[0].rstrip('.')}"
    return "with concise, reusable instructions"


def build_rewrite_suggestions(skill: DiscoveredSkill, findings: list[Finding]) -> dict:
    seen_actions: list[str] = []
    for finding in findings:
        action = REWRITE_ACTIONS.get(finding.code)
        if action and action not in seen_actions:
            seen_actions.append(action)

    rewritten_description = (
        f"Use this skill when {_description_trigger(skill)}, "
        f"and guide the user {_description_scope(skill)}."
    )

    if not seen_actions:
        seen_actions.append(
            "Keep the current structure and refine examples only if the runtime needs"
            " tighter guidance."
        )

    return {
        "headline": "Suggested rewrite",
        "rewritten_description": rewritten_description,
        "cleanup_actions": seen_actions[:5],
    }
