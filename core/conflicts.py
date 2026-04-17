from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re

from core.models import Conflict, ConflictDetectionResult, DiscoveredSkill

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
LARGE_COLLECTION_THRESHOLD = 8
SIMILARITY_CLUSTER_THRESHOLD = 0.18
SIMILARITY_COMPARE_THRESHOLD = 0.3
SEMANTIC_CLUSTER_THRESHOLD = 0.34
SEMANTIC_COMPARE_THRESHOLD = 0.42
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")
STOPWORDS = {
    "this",
    "that",
    "these",
    "those",
    "skill",
    "skills",
    "with",
    "from",
    "into",
    "when",
    "then",
    "than",
    "para",
    "como",
    "esta",
    "este",
    "estos",
    "estas",
    "using",
    "used",
    "usar",
    "uses",
    "your",
    "their",
    "them",
    "they",
    "work",
    "works",
    "tasks",
    "task",
    "need",
    "needs",
    "many",
    "across",
    "about",
    "only",
}
TOKEN_SYNONYMS = {
    "repository": "repo",
    "repositories": "repo",
    "project": "repo",
    "projects": "repo",
    "codebase": "repo",
    "documentation": "docs",
    "document": "docs",
    "documents": "docs",
    "readme": "docs",
    "guide": "docs",
    "guides": "docs",
    "cleanup": "clean",
    "tidy": "clean",
    "tidying": "clean",
    "refactor": "clean",
    "triage": "review",
    "audit": "review",
    "reviewing": "review",
    "reviews": "review",
    "summaries": "summary",
    "summarize": "summary",
    "summarizing": "summary",
    "notes": "summary",
    "findings": "issues",
    "problems": "issues",
    "problem": "issues",
    "issues": "issues",
    "bugs": "issues",
    "fix": "repair",
    "repairing": "repair",
    "verify": "check",
    "validation": "check",
    "validate": "check",
    "checking": "check",
}


@dataclass(frozen=True, slots=True)
class PairSignals:
    overlap_ratio: float
    semantic_overlap_ratio: float
    shared_sections: set[str]
    left_directives: dict[str, set[str]]
    right_directives: dict[str, set[str]]
    left_language: str | None
    right_language: str | None
    direct_policy_conflict: bool


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


def _normalize_token(token: str) -> str:
    normalized = token.lower().strip("_-")
    normalized = TOKEN_SYNONYMS.get(normalized, normalized)
    for suffix in ("ing", "ed", "es", "s"):
        if len(normalized) > 5 and normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return TOKEN_SYNONYMS.get(normalized, normalized)


def _semantic_signature(skill: DiscoveredSkill) -> set[str]:
    text = "\n".join(
        [
            skill.description,
            *skill.usage_lines,
            *skill.restriction_lines,
            *skill.examples,
            *skill.sections,
        ]
    ).lower()
    signature: set[str] = set()
    for token in TOKEN_RE.findall(text):
        normalized = _normalize_token(token)
        if len(normalized) < 4 or normalized in STOPWORDS:
            continue
        signature.add(normalized)
    return signature


def _overlap_ratio(left: DiscoveredSkill, right: DiscoveredSkill) -> float:
    left_tokens = _text_signature(left)
    right_tokens = _text_signature(right)
    if not left_tokens or not right_tokens:
        return 0.0
    shared = left_tokens & right_tokens
    base = min(len(left_tokens), len(right_tokens))
    return len(shared) / max(1, base)


def _semantic_overlap_ratio(left: DiscoveredSkill, right: DiscoveredSkill) -> float:
    left_tokens = _semantic_signature(left)
    right_tokens = _semantic_signature(right)
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


def _pair_signals(left: DiscoveredSkill, right: DiscoveredSkill) -> PairSignals:
    left_directives = _extract_directives(left.content)
    right_directives = _extract_directives(right.content)
    direct_policy_conflict = bool(
        (
            left_directives["shell"]
            and right_directives["shell"]
            and left_directives["shell"] != right_directives["shell"]
        )
        or (
            left_directives["operating_system"]
            and right_directives["operating_system"]
            and left_directives["operating_system"] != right_directives["operating_system"]
        )
        or (
            {
                frozenset(("never-ask", "ask")),
            }
            & {
                frozenset((left_policy, right_policy))
                for left_policy in left_directives["question_policy"]
                for right_policy in right_directives["question_policy"]
            }
        )
        or (
            {
                frozenset(("always-browse", "no-browse")),
            }
            & {
                frozenset((left_policy, right_policy))
                for left_policy in left_directives["web_policy"]
                for right_policy in right_directives["web_policy"]
            }
        )
        or left_directives["required_tools"] & right_directives["forbidden_tools"]
        or right_directives["required_tools"] & left_directives["forbidden_tools"]
    )
    return PairSignals(
        overlap_ratio=_overlap_ratio(left, right),
        semantic_overlap_ratio=_semantic_overlap_ratio(left, right),
        shared_sections=set(left.sections) & set(right.sections),
        left_directives=left_directives,
        right_directives=right_directives,
        left_language=_dominant_language(left),
        right_language=_dominant_language(right),
        direct_policy_conflict=direct_policy_conflict,
    )


def _is_similarity_edge(signals: PairSignals) -> bool:
    return (
        signals.overlap_ratio >= SIMILARITY_CLUSTER_THRESHOLD
        or signals.semantic_overlap_ratio >= SEMANTIC_CLUSTER_THRESHOLD
        or len(signals.shared_sections) >= 2
        or (
            signals.overlap_ratio >= 0.12
            and bool(signals.left_directives["role"] & signals.right_directives["role"])
        )
    )


def _should_compare_pair(
    total_skills: int,
    same_cluster: bool,
    signals: PairSignals,
) -> tuple[bool, str]:
    if total_skills <= LARGE_COLLECTION_THRESHOLD:
        return True, "full-scan"
    if same_cluster and (
        signals.overlap_ratio >= SIMILARITY_COMPARE_THRESHOLD
        or signals.semantic_overlap_ratio >= SEMANTIC_COMPARE_THRESHOLD
        or len(signals.shared_sections) >= 2
        or signals.direct_policy_conflict
    ):
        return True, "clustered"
    if signals.direct_policy_conflict:
        return True, "directive-override"
    return False, "skipped-by-clustering"


def _cluster_skills(skills: list[DiscoveredSkill]) -> dict[str, str]:
    parents = {skill.name: skill.name for skill in skills}

    def find(name: str) -> str:
        while parents[name] != name:
            parents[name] = parents[parents[name]]
            name = parents[name]
        return name

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left, right in combinations(skills, 2):
        if _is_similarity_edge(_pair_signals(left, right)):
            union(left.name, right.name)

    root_to_cluster: dict[str, str] = {}
    cluster_ids: dict[str, str] = {}
    for skill in skills:
        root = find(skill.name)
        cluster_id = root_to_cluster.setdefault(root, f"cluster-{len(root_to_cluster) + 1}")
        cluster_ids[skill.name] = cluster_id
    return cluster_ids


def _cluster_sizes(cluster_ids: dict[str, str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for cluster_id in cluster_ids.values():
        sizes[cluster_id] = sizes.get(cluster_id, 0) + 1
    return sizes


def _build_conflict(
    left: DiscoveredSkill,
    right: DiscoveredSkill,
    severity: str,
    category: str,
    evidence: list[str],
    *,
    overlap_ratio: float = 0.0,
    cluster_id: str | None = None,
    cluster_size: int = 0,
    comparison_context: str = "full-scan",
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
        cluster_id=cluster_id,
        cluster_size=cluster_size,
        comparison_context=comparison_context,
    )


def analyze_conflicts(skills: list[DiscoveredSkill]) -> ConflictDetectionResult:
    conflicts: list[Conflict] = []
    cluster_ids = _cluster_skills(skills)
    cluster_sizes = _cluster_sizes(cluster_ids)
    compared_pairs = 0
    compared_skill_pairs: list[tuple[str, str]] = []
    skipped_pairs = 0
    total_pairs = 0

    for left, right in combinations(skills, 2):
        total_pairs += 1
        signals = _pair_signals(left, right)
        left_cluster_id = cluster_ids[left.name]
        right_cluster_id = cluster_ids[right.name]
        same_cluster = left_cluster_id == right_cluster_id
        compare_pair, comparison_context = _should_compare_pair(
            len(skills),
            same_cluster,
            signals,
        )
        if not compare_pair:
            skipped_pairs += 1
            continue

        compared_pairs += 1
        compared_skill_pairs.append((left.name, right.name))
        conflict_cluster_id = left_cluster_id if same_cluster else "cross-cluster"
        conflict_cluster_size = cluster_sizes[left_cluster_id] if same_cluster else 0

        if (
            signals.left_language
            and signals.right_language
            and signals.left_language != signals.right_language
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "low",
                    "language",
                    [
                        (
                            f"{left.name} prefers "
                            f"{LANGUAGE_LABELS.get(signals.left_language, signals.left_language)}"
                        ),
                        (
                            f"{right.name} prefers "
                            f"{LANGUAGE_LABELS.get(signals.right_language, signals.right_language)}"
                        ),
                    ],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        if (
            signals.left_directives["shell"]
            and signals.right_directives["shell"]
            and signals.left_directives["shell"] != signals.right_directives["shell"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "shell",
                    [
                        f"{left.name}: {sorted(signals.left_directives['shell'])}",
                        f"{right.name}: {sorted(signals.right_directives['shell'])}",
                    ],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        if (
            signals.left_directives["operating_system"]
            and signals.right_directives["operating_system"]
            and signals.left_directives["operating_system"]
            != signals.right_directives["operating_system"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "operating-system",
                    [
                        f"{left.name}: {sorted(signals.left_directives['operating_system'])}",
                        f"{right.name}: {sorted(signals.right_directives['operating_system'])}",
                    ],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        if {
            frozenset(("never-ask", "ask")),
        } & {
            frozenset((left_policy, right_policy))
            for left_policy in signals.left_directives["question_policy"]
            for right_policy in signals.right_directives["question_policy"]
        }:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "confirmation-policy",
                    [
                        f"{left.name}: {sorted(signals.left_directives['question_policy'])}",
                        f"{right.name}: {sorted(signals.right_directives['question_policy'])}",
                    ],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        if {
            frozenset(("always-browse", "no-browse")),
        } & {
            frozenset((left_policy, right_policy))
            for left_policy in signals.left_directives["web_policy"]
            for right_policy in signals.right_directives["web_policy"]
        }:
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "web-policy",
                    [
                        f"{left.name}: {sorted(signals.left_directives['web_policy'])}",
                        f"{right.name}: {sorted(signals.right_directives['web_policy'])}",
                    ],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        for tool in sorted(
            signals.left_directives["required_tools"] & signals.right_directives["forbidden_tools"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "tooling",
                    [f"{left.name} requires `{tool}`", f"{right.name} forbids `{tool}`"],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )
        for tool in sorted(
            signals.right_directives["required_tools"] & signals.left_directives["forbidden_tools"]
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "high",
                    "tooling",
                    [f"{right.name} requires `{tool}`", f"{left.name} forbids `{tool}`"],
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        tone_role_evidence = _tone_or_role_conflicts(
            signals.left_directives, signals.right_directives
        )
        if tone_role_evidence and (
            signals.overlap_ratio >= 0.35
            or signals.semantic_overlap_ratio >= 0.45
            or len(signals.shared_sections) >= 2
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "medium",
                    "tone-role",
                    [
                        *tone_role_evidence,
                        f"overlap_ratio={round(signals.overlap_ratio, 2)}",
                        f"semantic_overlap_ratio={round(signals.semantic_overlap_ratio, 2)}",
                        f"shared_sections={sorted(signals.shared_sections)}",
                    ],
                    overlap_ratio=signals.overlap_ratio,
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
                )
            )

        if (
            signals.overlap_ratio >= 0.6
            or signals.semantic_overlap_ratio >= 0.58
            or len(signals.shared_sections) >= 3
        ):
            conflicts.append(
                _build_conflict(
                    left,
                    right,
                    "low" if signals.overlap_ratio < 0.75 else "medium",
                    "overlap",
                    [
                        f"overlap_ratio={round(signals.overlap_ratio, 2)}",
                        f"semantic_overlap_ratio={round(signals.semantic_overlap_ratio, 2)}",
                        f"shared_sections={sorted(signals.shared_sections)}",
                    ],
                    overlap_ratio=max(signals.overlap_ratio, signals.semantic_overlap_ratio),
                    cluster_id=conflict_cluster_id,
                    cluster_size=conflict_cluster_size,
                    comparison_context=comparison_context,
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
                            (
                                "semantic_overlap_ratio="
                                f"{round(signals.semantic_overlap_ratio, 2)}"
                            ),
                        ],
                        overlap_ratio=max(signals.overlap_ratio, signals.semantic_overlap_ratio),
                        cluster_id=conflict_cluster_id,
                        cluster_size=conflict_cluster_size,
                        comparison_context=comparison_context,
                    )
                )

    return ConflictDetectionResult(
        conflicts=sorted(
            conflicts,
            key=lambda item: (-item.priority, item.left_skill, item.right_skill, item.category),
        ),
        cluster_count=len(set(cluster_ids.values())),
        compared_pairs=compared_pairs,
        skipped_pairs=skipped_pairs,
        total_pairs=total_pairs,
        compared_skill_pairs=compared_skill_pairs,
    )


def detect_conflicts(skills: list[DiscoveredSkill]) -> list[Conflict]:
    return analyze_conflicts(skills).conflicts
