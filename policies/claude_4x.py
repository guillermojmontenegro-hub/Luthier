POLICY_PACK = {
    "name": "claude-4x",
    "version": "1.0",
    "rules_version": "1.1",
    "prompt_version": "1.1",
    "positive_signals": [
        "explicit delegation scope",
        "parallel-safe task splits",
        "clear collaboration handoffs",
    ],
    "negative_signals": [
        "ambiguous ownership",
        "overlapping delegated writes",
        "excessive blocking questions",
    ],
    "prompt_suffixes": {
        "skill-audit": (
            "Pay extra attention to delegation scope, explicit ownership, "
            "and whether parallel work "
            "is safe or ambiguous."
        ),
        "skill-compare": (
            "Focus on overlapping ownership, conflicting collaboration "
            "expectations, and unsafe task splits."
        ),
        "report-synthesis": (
            "Summarize the main collaboration, ownership, and delegation risks."
        ),
    },
    "scoring": {
        "positive_patterns": [
            "ownership",
            "delegate",
            "delegation",
            "parallel",
            "handoff",
            "worker",
            "explorer",
        ],
        "negative_patterns": [
            "ask clarifying questions",
            "blocking question",
            "overlapping",
            "same files",
        ],
        "negative_finding_codes": ["over-specified-workflow", "excessive-restrictions"],
        "positive_effects": {"specificity": 0.5, "maintainability": 0.35},
        "negative_effects": {"risk": 0.6, "maintainability": -0.5},
        "max_positive_hits": 3,
        "max_negative_hits": 3,
    },
}
