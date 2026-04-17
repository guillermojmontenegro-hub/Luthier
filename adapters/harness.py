from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class HarnessInvocation:
    command: list[str]
    stdin: str | None
    timeout_seconds: float
    output_mode: str
    model: str


class LLMHarness(Protocol):
    provider: str
