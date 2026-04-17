"""Optional LLM adapters."""

from adapters.claude_code import ClaudeCodeLLMAdapter
from adapters.codex import CodexLLMAdapter
from adapters.command import CommandLLMAdapter
from adapters.harness import HarnessInvocation, LLMHarness
from adapters.llm import (
    LLM_EVALUATION_SCHEMA,
    LLMAdapter,
    LLMEvaluationResult,
    LLMExecutionMetadata,
    LLMFinding,
    StructuredPrompt,
    parse_llm_evaluation,
)
from adapters.mock import MockLLMAdapter
from adapters.opencode import OpenCodeLLMAdapter


def create_adapter(provider: str) -> LLMAdapter:
    normalized = provider.strip().lower()
    if normalized == "mock":
        return MockLLMAdapter()
    if normalized == "codex":
        return CodexLLMAdapter()
    if normalized == "claude-code":
        return ClaudeCodeLLMAdapter()
    if normalized == "opencode":
        return OpenCodeLLMAdapter()
    raise ValueError(f"Unsupported LLM provider: {provider}")


__all__ = [
    "ClaudeCodeLLMAdapter",
    "CodexLLMAdapter",
    "CommandLLMAdapter",
    "create_adapter",
    "HarnessInvocation",
    "LLMAdapter",
    "LLM_EVALUATION_SCHEMA",
    "LLMEvaluationResult",
    "LLMExecutionMetadata",
    "LLMFinding",
    "LLMHarness",
    "MockLLMAdapter",
    "OpenCodeLLMAdapter",
    "StructuredPrompt",
    "parse_llm_evaluation",
]
