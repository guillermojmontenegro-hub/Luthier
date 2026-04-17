from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from adapters.command import SchemaAwareCommandLLMAdapter


class CodexLLMAdapter(SchemaAwareCommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="codex",
            default_command="codex",
            command_env_var="LUTHIER_CODEX_CMD",
            default_model="gpt-5",
            model_env_var="LUTHIER_CODEX_MODEL",
            runner=runner,
        )

    def build_schema_aware_arguments(self, schema_path: Path, output_path: Path) -> list[str]:
        return [
            "exec",
            "--model",
            self.resolve_model(),
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "-",
        ]

    def output_mode(self) -> str:
        return "schema-file+last-message"
