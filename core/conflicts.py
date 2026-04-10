from __future__ import annotations

from itertools import combinations

from core.models import Conflict, DiscoveredSkill

LANGUAGE_LABELS = {"en": "English", "es": "Spanish"}
SEVERITY_PRIORITY = {"high": 3, "medium": 2, "low": 1}
TONE_SIGNAL_PATTERNS = {
    "supportive": (
        "warm",
        "encouraging",
        "supportive",
        "kind",
        "empathetic",
        "collaborative",
        "patient",
    ),
    "strict": (
        "blunt",
        "terse",
        "strict",
        "skeptical",
        "critical",
        "harsh",
        "uncompromising",
    ),
}
ROLE_SIGNAL_PATTERNS = {
    "builder": (
        "implement",
        "implementation",
        "write code",
        "coding agent",
        "production work",
        "make code changes",
    ),
    "reviewer": (
        "review mindset",
        "code review",
        "reviewer",
        "identify bugs",
        "findings must be the primary focus",
        "prioritise identifying bugs",
    ),
    "coach": (
        "teacher",
        "coach",
        "pair",
        "onboarding",
        "explain concepts",
        "unblock",
    ),
    "enforcer": (
        "compliance",
        "policy enforcement",
        "enforce",
        "must refuse",
        "security auditor",
    ),
}
ROLE_CONFLICTS = {
    frozenset(("builder", "reviewer")),
    frozenset(("builder", "enforcer")),
    frozenset(("coach", "enforcer")),
}


def _extract_directives(content: str) -> dict[str, set[str]]:
    lowered = content.lower()
    directives: dict[str, set[str]] = {
        "shell": set(),
        "operating_system": set(),
        "question_policy": set(),
        "web_policy": set(),
        "required_tools": set(),
        "forbidden_tools": set(),
        "tone": set(),
        "role": set(),
    }

    if "always use powershell" in lowered:
        directives["shell"].add("powershell")
    if "always use bash" in lowered or "use `bash`" in lowered or "use bash" in lowered:
        directives["shell"].add("bash")

    if "always use windows paths" in lowered or "windows-only" in lowered:
        directives["operating_system"].add("windows")
    if "linux-only" in lowered or "unix-only" in lowered or "macos-only" in lowered:
        directives["operating_system"].add("unix")

    if "never ask follow-up questions" in lowered or "do not ask follow-up questions" in lowered:
        directives["question_policy"].add("never-ask")
    if "ask follow-up questions" in lowered or "ask clarifying questions" in lowered:
        directives["question_policy"].add("ask")

    if "always browse the web" in lowered or "must browse the web" in lowered:
        directives["web_policy"].add("always-browse")
    if "never browse the web" in lowered or "do not browse the web" in lowered:
        directives["web_policy"].add("no-browse")

    for tool in ("rg", "grep", "git", "python", "node"):
        if f"always use `{tool}`" in lowered or f"must use `{tool}`" in lowered:
            directives["required_tools"].add(tool)
        if f"never use `{tool}`" in lowered or f"do not use `{tool}`" in lowered:
            directives["forbidden_tools"].add(tool)

    for tone, patterns in TONE_SIGNAL_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            directives["tone"].add(tone)

    for role, patterns in ROLE_SIGNAL_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            directives["role"].add(role)

    return directives


def _dominant_language(skill: DiscoveredSkill) -> str | None:
    ranked = sorted(skill.language_mix.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] == 0:
        return None
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


def _text_signature(skill: DiscoveredSkill) -> set[str]:
    return {
        token.strip(".,:;`'\"()[]{}")
        for token in skill.content.lower().split()
        if len(token.strip(".,:;`'\"()[]{}")) >= 5
    }


def _overlap_ratio(left: DiscoveredSkill, right: DiscoveredSkill) -> float:
    left_tokens = _text_signature(left)
    right_tokens = _text_signature(right)
    if not left_tokens or not right_tokens:
        return 0.0
    shared = left_tokens & right_tokens
    base = min(len(left_tokens), len(right_tokens))
    return len(shared) / max(1, base)


def _description_is_generic(skill: DiscoveredSkill) -> bool:
    lowered = skill.description.lower()
    return any(
        token in lowered
        for token in ("general", "useful", "helpful", "many things", "varios", "cosas")
    )


def _tone_or_role_conflicts(
    left_directives: dict[str, set[str]],
    right_directives: dict[str, set[str]],
) -> list[str]:
    evidence: list[str] = []

    if {
        frozenset(("supportive", "strict")),
    } & {
        frozenset((left_tone, right_tone))
        for left_tone in left_directives["tone"]
        for right_tone in right_directives["tone"]
    }:
        evidence.append(
            f"tone: {sorted(left_directives['tone'])} vs {sorted(right_directives['tone'])}"
        )

    for left_role in left_directives["role"]:
        for right_role in right_directives["role"]:
            if frozenset((left_role, right_role)) in ROLE_CONFLICTS:
                evidence.append(
                    f"role: {sorted(left_directives['role'])} vs {sorted(right_directives['role'])}"
                )
                return evidence

    return evidence


def _recommendation_for(
    category: str, left: DiscoveredSkill, right: DiscoveredSkill, overlap_ratio: float = 0.0
) -> str:
    if category in {"shell", "operating-system", "tooling"}:
        return "Split runtime-specific guidance or scope each skill to a compatible environment."
    if category in {"confirmation-policy", "web-policy", "tone-role"}:
        return (
            "Align the policies or separate the skills by scenario so the runtime "
            "picks one unambiguously."
        )
    if category == "misleading-discovery":
        return (
            "Rename at least one skill and sharpen both opening descriptions so "
            "selection is less ambiguous."
        )
    if category == "overlap":
        if overlap_ratio >= 0.75:
            return (
                "Consider merging the skills or making their responsibilities explicitly distinct."
            )
        return (
            "Clarify the boundary between both skills and rename one if they target adjacent tasks."
        )
    if category == "language":
        return (
            "Choose a dominant operating language or document when each "
            "language-specific variant should trigger."
        )
    return "Review the overlap and tighten each skill's trigger conditions."


def _build_conflict(
    left: DiscoveredSkill,
    right: DiscoveredSkill,
    severity: str,
    category: str,
    evidence: list[str],
    *,
    overlap_ratio: float = 0.0,
) -> Conflict:
    priority = SEVERITY_PRIORITY[severity] * 100
    if category == "overlap":
        priority += round(overlap_ratio * 100)
    elif category == "misleading-discovery":
        priority += 40
    elif category in {"shell", "operating-system", "tooling"}:
        priority += 30
    else:
        priority += 10
    return Conflict(
        left_skill=left.name,
        right_skill=right.name,
        severity=severity,
        category=category,
        evidence=evidence,
        priority=priority,
        recommendation=_recommendation_for(category, left, right, overlap_ratio),
    )


def detect_conflicts(skills: list[DiscoveredSkill]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for left, right in combinations(skills, 2):
        left_directives = _extract_directives(left.content)
        right_directives = _extract_directives(right.content)

        left_language = _dominant_language(left)
        right_language = _dominant_language(right)
        if left_language and right_language and left_language != right_language:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "low",
                    "language",
                    [
                        f"{left.name} prefers {LANGUAGE_LABELS.get(left_language, left_language)}",
                        (
                            f"{right.name} prefers "
                            f"{LANGUAGE_LABELS.get(right_language, right_language)}"
                        ),
                    ],
                )
            )

        if (
            left_directives["shell"]
            and right_directives["shell"]
            and left_directives["shell"] != right_directives["shell"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "shell",
                    [
                        f"{left.name}: {sorted(left_directives['shell'])}",
                        f"{right.name}: {sorted(right_directives['shell'])}",
                    ],
                )
            )

        if (
            left_directives["operating_system"]
            and right_directives["operating_system"]
            and left_directives["operating_system"] != right_directives["operating_system"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "operating-system",
                    [
                        f"{left.name}: {sorted(left_directives['operating_system'])}",
                        f"{right.name}: {sorted(right_directives['operating_system'])}",
                    ],
                )
            )

        if {
            frozenset(("never-ask", "ask")),
        } & {
            frozenset((left_policy, right_policy))
            for left_policy in left_directives["question_policy"]
            for right_policy in right_directives["question_policy"]
        }:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "confirmation-policy",
                    [
                        f"{left.name}: {sorted(left_directives['question_policy'])}",
                        f"{right.name}: {sorted(right_directives['question_policy'])}",
                    ],
                )
            )

        if {
            frozenset(("always-browse", "no-browse")),
        } & {
            frozenset((left_policy, right_policy))
            for left_policy in left_directives["web_policy"]
            for right_policy in right_directives["web_policy"]
        }:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "web-policy",
                    [
                        f"{left.name}: {sorted(left_directives['web_policy'])}",
                        f"{right.name}: {sorted(right_directives['web_policy'])}",
                    ],
                )
            )

        for tool in sorted(left_directives["required_tools"] & right_directives["forbidden_tools"]):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "tooling",
                    [f"{left.name} requires `{tool}`", f"{right.name} forbids `{tool}`"],
                )
            )
        for tool in sorted(right_directives["required_tools"] & left_directives["forbidden_tools"]):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "tooling",
                    [f"{right.name} requires `{tool}`", f"{left.name} forbids `{tool}`"],
                )
            )

        overlap_ratio = _overlap_ratio(left, right)
        shared_sections = set(left.sections) & set(right.sections)
        tone_role_evidence = _tone_or_role_conflicts(left_directives, right_directives)

        if tone_role_evidence and (overlap_ratio >= 0.35 or len(shared_sections) >= 2):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "tone-role",
                    [
                        *tone_role_evidence,
                        f"overlap_ratio={round(overlap_ratio, 2)}",
                        f"shared_sections={sorted(shared_sections)}",
                    ],
                    overlap_ratio=overlap_ratio,
                )
            )

        if overlap_ratio >= 0.6 or len(shared_sections) >= 3:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "low" if overlap_ratio < 0.75 else "medium",
                    "overlap",
                    [
                        f"overlap_ratio={round(overlap_ratio, 2)}",
                        f"shared_sections={sorted(shared_sections)}",
                    ],
                    overlap_ratio=overlap_ratio,
                )
            )
            if _description_is_generic(left) or _description_is_generic(right):
                conflicts.append(
                    _build_conflict(
                        left,
                        right,
                        "medium",
                        "misleading-discovery",
                        [
                            f"{left.name} description={left.description or '(empty)'}",
                            f"{right.name} description={right.description or '(empty)'}",
                        ],
                        overlap_ratio=overlap_ratio,
                    )
                )

    return sorted(
        conflicts,
        key=lambda item: (-item.priority, item.left_skill, item.right_skill, item.category),
    )
