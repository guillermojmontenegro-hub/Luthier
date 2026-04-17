from __future__ import annotations

import subprocess
from collections.abc import Callable

from adapters.command import CommandLLMAdapter


class CodexLLMAdapter(CommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="codex",
            default_command="codex-llm",
            command_env_var="LUTHIER_CODEX_CMD",
            runner=runner,
        )
