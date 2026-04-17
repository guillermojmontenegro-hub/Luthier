from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adapters.harness import HarnessInvocation, LLMHarness
from adapters.llm import (
    LLM_EVALUATION_SCHEMA,
    LLMEvaluationResult,
    LLMExecutionMetadata,
    StructuredPrompt,
    parse_llm_evaluation,
)


class CommandLLMAdapter(ABC):
    def __init__(
        self,
        *,
        provider: str,
        default_command: str,
        command_env_var: str,
        default_model: str,
        model_env_var: str,
        timeout_seconds: float = 90.0,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.provider = provider
        self.default_command = default_command
        self.command_env_var = command_env_var
        self.default_model = default_model
        self.model_env_var = model_env_var
        self.timeout_seconds = timeout_seconds
        self._runner = runner or subprocess.run

    def resolve_command_prefix(self) -> list[str]:
        configured = os.environ.get(self.command_env_var, "").strip()
        if configured:
            return shlex.split(configured)
        return [self.default_command]

    def resolve_model(self) -> str:
        configured = os.environ.get(self.model_env_var, "").strip()
        if configured:
            return configured
        return self.default_model

    @property
    def harness_name(self) -> str:
        return f"{self.provider}-cli"

    def evaluate(self, prompt: StructuredPrompt) -> LLMEvaluationResult:
        with tempfile.TemporaryDirectory(prefix=f"luthier-{self.provider}-") as tmp:
            workspace = Path(tmp)
            schema_path = workspace / "llm-output.schema.json"
            output_path = workspace / "llm-output.json"
            schema_path.write_text(
                json.dumps(LLM_EVALUATION_SCHEMA, ensure_ascii=True, indent=2) + "\n",
                encoding="utf-8",
            )
            invocation = HarnessInvocation(
                command=self.build_command(prompt, schema_path, output_path),
                stdin=self.build_stdin(prompt),
                timeout_seconds=self.timeout_seconds,
                output_mode=self.output_mode(),
                model=self.resolve_model(),
            )
            try:
                completed = self._runner(
                    invocation.command,
                    input=invocation.stdin,
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=invocation.timeout_seconds,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"{self.provider} adapter could not find executable "
                    f"{invocation.command[0]!r}. Set {self.command_env_var} to a compatible "
                    "non-interactive CLI command."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"{self.provider} adapter timed out after {invocation.timeout_seconds:.0f}s."
                ) from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                raise RuntimeError(
                    f"{self.provider} adapter command failed with exit code {exc.returncode}. "
                    f"stderr={stderr or '(empty)'}"
                ) from exc

            payload = self.parse_payload(
                stdout=completed.stdout,
                stderr=completed.stderr,
                output_path=output_path,
            )
            execution = LLMExecutionMetadata(
                provider=self.provider,
                model=payload.get("model", invocation.model),
                harness=self.harness_name,
                command=invocation.command,
                timeout_seconds=invocation.timeout_seconds,
                output_mode=invocation.output_mode,
            )
            return parse_llm_evaluation(payload, prompt.prompt_type, execution=execution)

    def build_stdin(self, prompt: StructuredPrompt) -> str | None:
        return self.render_prompt(prompt)

    def render_prompt(self, prompt: StructuredPrompt) -> str:
        return (
            "Return exactly one JSON object matching the requested contract.\n\n"
            f"{json.dumps(prompt.to_dict(), ensure_ascii=True, indent=2)}\n"
        )

    @abstractmethod
    def build_command(
        self,
        prompt: StructuredPrompt,
        schema_path: Path,
        output_path: Path,
    ) -> list[str]:
        """Build the non-interactive provider command."""

    @abstractmethod
    def output_mode(self) -> str:
        """Describe the structured output strategy used by the provider."""

    def parse_payload(self, *, stdout: str, stderr: str, output_path: Path) -> dict[str, Any]:
        del stderr
        output_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
        if output_text:
            return self._load_json(output_text)

        stdout = stdout.strip()
        if not stdout:
            raise RuntimeError(
                f"{self.provider} adapter returned empty stdout. "
                "Expected structured JSON output from the runtime."
            )
        return self._load_json(stdout)

    def _load_json(self, text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{self.provider} adapter returned invalid JSON. "
                "Expected a JSON object matching the structured LLM contract."
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"{self.provider} adapter returned JSON of type {type(payload).__name__}, "
                "but a JSON object was required."
            )
        return payload


class SchemaAwareCommandLLMAdapter(CommandLLMAdapter, LLMHarness):
    def build_command(
        self,
        prompt: StructuredPrompt,
        schema_path: Path,
        output_path: Path,
    ) -> list[str]:
        del prompt
        return self.resolve_command_prefix() + self.build_schema_aware_arguments(schema_path, output_path)

    @abstractmethod
    def build_schema_aware_arguments(self, schema_path: Path, output_path: Path) -> list[str]:
        """Build provider-specific CLI arguments for schema-backed structured output."""
