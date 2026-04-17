POLICY_PACK = {
    "name": "gemini-25",
    "version": "1.0",
    "rules_version": "1.0",
    "prompt_version": "1.0",
    "positive_signals": [
        "explicit stepwise thinking boundaries",
        "clear multimodal or tool-routing triggers",
        "grounded retrieval or verification guidance",
    ],
    "negative_signals": [
        "unbounded chain-of-thought forcing",
        "ambiguous retrieval expectations",
        "tool usage without grounding criteria",
    ],
    "prompt_suffixes": {
        "skill-audit": (
            "Pay extra attention to grounded retrieval, bounded reasoning instructions, "
            "and whether multimodal or tool-routing triggers are explicit."
        ),
        "skill-compare": (
            "Focus on conflicts around retrieval, tool routing, and overly prescriptive "
            "reasoning instructions."
        ),
        "report-synthesis": (
            "Highlight grounding risks, tool-routing clarity, and multimodal trigger quality."
        ),
    },
    "scoring": {
        "positive_patterns": [
            "grounded",
            "verify with sources",
            "tool routing",
            "multimodal",
            "image",
            "pdf",
            "structured output",
        ],
        "negative_patterns": [
            "always reveal your reasoning",
            "show chain of thought",
            "must think step by step",
            "always use every tool",
        ],
        "negative_finding_codes": ["rigid-tooling-or-sequence", "description-vague"],
        "positive_effects": {"specificity": 0.45, "discoverability": 0.3},
        "negative_effects": {"risk": 0.65, "maintainability": -0.4},
        "max_positive_hits": 3,
        "max_negative_hits": 3,
    },
}
