from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Callable

from adapters.llm import LLMEvaluationResult, StructuredPrompt, parse_llm_evaluation


class CommandLLMAdapter:
    def __init__(
        self,
        *,
        provider: str,
        default_command: str,
        command_env_var: str,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.provider = provider
        self.default_command = default_command
        self.command_env_var = command_env_var
        self._runner = runner or subprocess.run

    def resolve_command(self) -> list[str]:
        configured = os.environ.get(self.command_env_var, "").strip()
        if configured:
            return shlex.split(configured)
        return [self.default_command]

    def evaluate(self, prompt: StructuredPrompt) -> LLMEvaluationResult:
        command = self.resolve_command()
        try:
            completed = self._runner(
                command,
                input=json.dumps(prompt.to_dict(), ensure_ascii=True),
                capture_output=True,
                check=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"{self.provider} adapter could not find executable {command[0]!r}. "
                f"Set {self.command_env_var} to a compatible wrapper command."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(
                f"{self.provider} adapter command failed with exit code {exc.returncode}. "
                f"stderr={stderr or '(empty)'}"
            ) from exc

        stdout = completed.stdout.strip()
        if not stdout:
            raise RuntimeError(
                f"{self.provider} adapter returned empty stdout. "
                f"Expected a JSON object matching the structured LLM contract."
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{self.provider} adapter returned invalid JSON. "
                "Expected a JSON object on stdout."
            ) from exc

        return parse_llm_evaluation(payload, prompt.prompt_type)
