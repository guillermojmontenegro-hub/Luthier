POLICY_PACK = {
    "name": "openai-gpt5",
    "version": "1.0",
    "rules_version": "1.1",
    "prompt_version": "1.1",
    "positive_signals": [
        "clear decision boundary",
        "structured tool routing",
        "up-to-date verification triggers",
    ],
    "negative_signals": [
        "stale factual assumptions",
        "unbounded browsing",
        "hidden model-specific forcing",
    ],
    "prompt_suffixes": {
        "skill-audit": (
            "Pay extra attention to decision boundaries, freshness-sensitive instructions, "
            "and whether browsing guidance is explicit but bounded."
        ),
        "skill-compare": (
            "Emphasize overlapping triggers, stale-assumption risk, and contradictory web guidance."
        ),
        "report-synthesis": (
            "Highlight freshness-sensitive issues, browsing discipline, and discoverability conflicts."
        ),
    },
    "scoring": {
        "positive_patterns": [
            "decision boundary",
            "when to use",
            "when not to use",
            "latest",
            "official",
            "structured",
            "browse",
        ],
        "negative_patterns": [
            "always browse the web",
            "must browse the web",
            "never browse the web",
            "always use",
            "must use",
            "never use",
        ],
        "negative_finding_codes": ["rigid-tooling-or-sequence", "description-vague"],
        "positive_effects": {"discoverability": 0.4, "specificity": 0.45},
        "negative_effects": {"risk": 0.7, "maintainability": -0.45},
        "max_positive_hits": 3,
        "max_negative_hits": 3,
    },
}
