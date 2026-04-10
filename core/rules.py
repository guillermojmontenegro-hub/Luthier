from __future__ import annotations

from core.models import DiscoveredSkill, EvaluationProfile, Finding, SkillMetrics
from core.parser import extract_list_lines, strip_code_blocks

VAGUE_TERMS = (
    "helpful",
    "useful",
    "good",
    "best",
    "general",
    "flexible",
    "powerful",
    "cosas",
    "varios",
)
RIGID_SEQUENCE_MARKERS = (
    "first ",
    "then ",
    "after that",
    "finally ",
    "step 1",
    "step 2",
    "step 3",
)
RIGID_TOOL_MARKERS = ("always use", "must use", "never use", "do not use")


def _normalized_line(line: str) -> str:
    return " ".join(line.lower().replace("`", "").split()).strip(" .,:;")


def _duplicate_instruction_lines(skill: DiscoveredSkill) -> list[str]:
    counts: dict[str, int] = {}
    duplicates: list[str] = []
    candidate_lines = [*skill.usage_lines, *skill.restriction_lines]
    if not candidate_lines:
        candidate_lines = extract_list_lines(strip_code_blocks(skill.content))
    for line in candidate_lines:
        normalized = _normalized_line(line)
        if len(normalized) < 12:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
        if counts[normalized] == 2:
            duplicates.append(line.strip())
    return duplicates


def _forced_tool_lines(skill: DiscoveredSkill) -> list[str]:
    forced: list[str] = []
    for line in skill.restriction_lines:
        lowered = line.lower()
        if any(marker in lowered for marker in RIGID_TOOL_MARKERS):
            forced.append(line)
    return forced


def _has_rigid_sequence(skill: DiscoveredSkill) -> bool:
    lowered = strip_code_blocks(skill.content).lower()
    return sum(lowered.count(marker) for marker in RIGID_SEQUENCE_MARKERS) >= 2


def evaluate_rules(
    skill: DiscoveredSkill, metrics: SkillMetrics, profile: EvaluationProfile
) -> list[Finding]:
    findings: list[Finding] = []
    list_line_count = len(extract_list_lines(strip_code_blocks(skill.content)))

    if metrics.description_tokens_estimate > 80:
        findings.append(
            Finding(
                code="description-too-long",
                severity="medium",
                message="The skill description is too long for reliable discovery.",
                evidence=[skill.description[:160]],
                recommendation=(
                    "Compress the opening description to a sharper scope and trigger signal."
                ),
            )
        )

    if metrics.description_tokens_estimate < 6 or any(
        term in skill.description.lower() for term in VAGUE_TERMS
    ):
        findings.append(
            Finding(
                code="description-vague",
                severity="medium",
                message="The description is weakly discriminative.",
                evidence=[skill.description or "(empty description)"],
                recommendation="State when the skill should be used and what it explicitly avoids.",
            )
        )

    missing_refs = [ref.path for ref in skill.references if not ref.exists]
    if missing_refs:
        findings.append(
            Finding(
                code="broken-references",
                severity="high",
                message="Referenced files are missing.",
                evidence=missing_refs,
                recommendation="Remove stale references or add the missing files.",
            )
        )

    if (
        any(signal in skill.platform_signals for signal in ("powershell", "cmd.exe", "windows"))
        and profile.operating_system != "windows"
    ):
        findings.append(
            Finding(
                code="platform-specific-instructions",
                severity="medium",
                message=(
                    "The skill contains platform-specific instructions that may not be portable."
                ),
                evidence=skill.platform_signals,
                recommendation=(
                    "Document alternatives per OS or narrow the supported platform explicitly."
                ),
            )
        )

    active_languages = [lang for lang, hits in skill.language_mix.items() if hits > 0]
    if len(active_languages) > 1:
        findings.append(
            Finding(
                code="mixed-language",
                severity="low",
                message="The skill mixes multiple languages.",
                evidence=[
                    f"{lang}={skill.language_mix[lang]}" for lang in sorted(skill.language_mix)
                ],
                recommendation=(
                    "Keep the operational instructions in one dominant language "
                    "unless multilingual support is required."
                ),
            )
        )

    if metrics.restriction_count >= max(6, metrics.imperative_steps * 2):
        findings.append(
            Finding(
                code="excessive-restrictions",
                severity="medium",
                message="The skill may be over-constrained.",
                evidence=[
                    f"restrictions={metrics.restriction_count}",
                    f"imperatives={metrics.imperative_steps}",
                ],
                recommendation=(
                    "Reduce rigid wording to the cases where it materially improves behavior."
                ),
            )
        )

    forced_tool_lines = _forced_tool_lines(skill)
    if len(forced_tool_lines) >= 2 or (forced_tool_lines and _has_rigid_sequence(skill)):
        findings.append(
            Finding(
                code="rigid-tooling-or-sequence",
                severity="medium",
                message="The skill appears to force tools or execution order too rigidly.",
                evidence=forced_tool_lines[:4] or skill.restriction_lines[:4],
                recommendation=(
                    "Keep hard requirements only for cases where compatibility "
                    "or correctness depends on them."
                ),
            )
        )

    if (
        max(metrics.imperative_steps, list_line_count) >= 8
        and metrics.example_count <= 1
        and metrics.restriction_count >= 3
    ):
        findings.append(
            Finding(
                code="over-specified-workflow",
                severity="medium",
                message=(
                    "The skill prescribes a detailed workflow that may be "
                    "narrower than its stated purpose."
                ),
                evidence=[
                    f"imperatives={metrics.imperative_steps}",
                    f"list_lines={list_line_count}",
                    f"restrictions={metrics.restriction_count}",
                    f"examples={metrics.example_count}",
                ],
                recommendation=(
                    "Separate required constraints from optional guidance and "
                    "compress procedural detail."
                ),
            )
        )

    duplicate_lines = _duplicate_instruction_lines(skill)
    if duplicate_lines:
        findings.append(
            Finding(
                code="duplicated-instructions",
                severity="low",
                message="The skill repeats operational instructions.",
                evidence=duplicate_lines[:4],
                recommendation=(
                    "Keep each instruction once and remove repeated wording "
                    "that increases context cost."
                ),
            )
        )

    if metrics.total_tokens_estimate > 700 and metrics.instruction_density < 0.02:
        findings.append(
            Finding(
                code="low-signal-content",
                severity="medium",
                message="The skill has high context cost relative to operational guidance.",
                evidence=[
                    f"tokens={metrics.total_tokens_estimate}",
                    f"instruction_density={metrics.instruction_density}",
                ],
                recommendation=(
                    "Remove narrative content and keep only operational constraints and examples."
                ),
            )
        )

    return findings
