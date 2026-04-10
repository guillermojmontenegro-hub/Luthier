from __future__ import annotations

from core.models import DiscoveredSkill, SkillMetrics
from core.parser import extract_list_lines, strip_code_blocks


RESTRICTION_MARKERS = ("must", "always", "never", "required", "debe", "siempre", "nunca", "obligatorio")
TOOL_MARKERS = ("rg", "grep", "git", "python", "node", "npm", "uv", "bash", "sh", "docker", "pytest")
NON_OPERATIONAL_MARKERS = ("why", "background", "philosophy", "motivation", "rationale", "contexto", "filosofia")
IMPERATIVE_MARKERS = (
    "use",
    "run",
    "create",
    "write",
    "add",
    "avoid",
    "implement",
    "prefer",
    "read",
    "update",
    "usa",
    "ejecuta",
    "crea",
    "agrega",
    "evita",
    "implementa",
    "lee",
)


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4)) if text.strip() else 0


def _count_restrictions(text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in RESTRICTION_MARKERS)


def _count_tools(text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in TOOL_MARKERS)


def _count_imperatives(list_lines: list[str]) -> int:
    total = 0
    for line in list_lines:
        lowered = line.lower()
        if any(lowered.startswith(marker) for marker in IMPERATIVE_MARKERS):
            total += 1
    return total


def compute_metrics(skill: DiscoveredSkill) -> SkillMetrics:
    stripped = strip_code_blocks(skill.content)
    list_lines = extract_list_lines(stripped)
    total_chars = len(skill.content)
    total_tokens = estimate_tokens(skill.content)
    description_tokens = estimate_tokens(skill.description)
    narrative_hits = sum(stripped.lower().count(marker) for marker in NON_OPERATIONAL_MARKERS)
    non_operational_ratio = round(min(1.0, narrative_hits / max(1, len(skill.sections) + len(list_lines))), 3)
    instruction_density = round(len(list_lines) / max(1, total_tokens), 3)
    context_cost_score = round(min(10.0, total_tokens / 120), 2)

    return SkillMetrics(
        description_chars=len(skill.description),
        description_tokens_estimate=description_tokens,
        total_chars=total_chars,
        total_tokens_estimate=total_tokens,
        section_count=len(skill.sections),
        imperative_steps=_count_imperatives(list_lines),
        restriction_count=_count_restrictions(stripped),
        example_count=len(skill.examples),
        tool_reference_count=_count_tools(stripped),
        non_operational_ratio=non_operational_ratio,
        instruction_density=instruction_density,
        context_cost_score=context_cost_score,
    )
