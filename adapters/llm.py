from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class StructuredPrompt:
    prompt_type: str
    payload: dict


class LLMAdapter(Protocol):
    def evaluate(self, prompt: StructuredPrompt) -> dict:
        """Return structured findings without coupling the core to a provider."""
