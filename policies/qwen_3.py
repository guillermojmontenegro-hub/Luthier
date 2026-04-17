POLICY_PACK = {
    "name": "qwen-3",
    "version": "1.0",
    "rules_version": "1.0",
    "prompt_version": "1.0",
    "positive_signals": [
        "clear bilingual or multilingual intent",
        "cost-aware reasoning boundaries",
        "explicit coding and tool-use scope",
    ],
    "negative_signals": [
        "language switching without purpose",
        "unbounded verbosity",
        "tool forcing without fallback guidance",
    ],
    "prompt_suffixes": {
        "skill-audit": (
            "Pay extra attention to language consistency, coding-task scope, "
            "and whether tool use is explicit but not over-forced."
        ),
        "skill-compare": (
            "Emphasize multilingual overlap, verbosity drift, and contradictory "
            "tool or coding expectations."
        ),
        "report-synthesis": (
            "Summarize multilingual clarity, cost-awareness, and coding-scope risks."
        ),
    },
    "scoring": {
        "positive_patterns": [
            "concise",
            "bilingual",
            "multilingual",
            "coding",
            "fallback",
            "structured",
            "summarize",
        ],
        "negative_patterns": [
            "be maximally detailed",
            "always answer in two languages",
            "must use python",
            "must use every available tool",
        ],
        "negative_finding_codes": ["language-mix", "rigid-tooling-or-sequence"],
        "positive_effects": {"maintainability": 0.3, "specificity": 0.35},
        "negative_effects": {"risk": 0.6, "discoverability": -0.35},
        "max_positive_hits": 3,
        "max_negative_hits": 3,
    },
}
