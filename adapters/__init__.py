"""Optional LLM adapters."""

from adapters.llm import (
    LLMAdapter,
    LLMEvaluationResult,
    LLMFinding,
    StructuredPrompt,
    parse_llm_evaluation,
)
from adapters.mock import MockLLMAdapter

__all__ = [
    "LLMAdapter",
    "LLMEvaluationResult",
    "LLMFinding",
    "MockLLMAdapter",
    "StructuredPrompt",
    "parse_llm_evaluation",
]
