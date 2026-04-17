from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from adapters.command import SchemaAwareCommandLLMAdapter


class ClaudeCodeLLMAdapter(SchemaAwareCommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="claude-code",
            default_command="claude",
            command_env_var="LUTHIER_CLAUDE_CODE_CMD",
            default_model="sonnet",
            model_env_var="LUTHIER_CLAUDE_CODE_MODEL",
            runner=runner,
        )

    def build_schema_aware_arguments(self, schema_path: Path, output_path: Path) -> list[str]:
        del output_path
        return [
            "--print",
            "--model",
            self.resolve_model(),
            "--output-format",
            "json",
            "--input-format",
            "text",
            "--permission-mode",
            "dontAsk",
            "--json-schema",
            schema_path.read_text(encoding="utf-8"),
        ]

    def output_mode(self) -> str:
        return "json-stdout+schema-flag"
