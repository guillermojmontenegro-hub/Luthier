POLICY_PACK = {
    "name": "generic-agentic",
    "version": "1.0",
    "rules_version": "1.0",
    "prompt_version": "1.0",
    "positive_signals": ["clear trigger", "bounded scope", "portable steps"],
    "negative_signals": ["vague description", "broken references", "platform lock-in"],
    "prompt_suffixes": {
        "skill-audit": "Prioritize scope clarity, portability, and bounded instructions.",
        "skill-compare": "Focus on overlap, trigger ambiguity, and runtime compatibility.",
        "report-synthesis": "Summarize the main static risks without inventing new categories.",
    },
    "scoring": {
        "positive_patterns": ["use this skill when", "do not use", "avoid ", "portable", "cross-platform"],
        "negative_patterns": ["always use powershell", "always use windows paths", "rewrite everything"],
        "negative_finding_codes": ["description-vague", "broken-references"],
        "positive_effects": {"discoverability": 0.35, "specificity": 0.25},
        "negative_effects": {"risk": 0.5, "portability": -0.35},
        "max_positive_hits": 3,
        "max_negative_hits": 2,
    },
}
