from __future__ import annotations

import subprocess
from collections.abc import Callable

from adapters.command import CommandLLMAdapter


class ClaudeCodeLLMAdapter(CommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="claude-code",
            default_command="claude-llm",
            command_env_var="LUTHIER_CLAUDE_CODE_CMD",
            runner=runner,
        )
