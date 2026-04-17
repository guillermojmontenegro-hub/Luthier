from __future__ import annotations

import subprocess
from collections.abc import Callable

from adapters.command import CommandLLMAdapter


class OpenCodeLLMAdapter(CommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="opencode",
            default_command="opencode-llm",
            command_env_var="LUTHIER_OPENCODE_CMD",
            runner=runner,
        )
