from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adapters.command import CommandLLMAdapter


class OpenCodeLLMAdapter(CommandLLMAdapter):
    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(
            provider="opencode",
            default_command="opencode",
            command_env_var="LUTHIER_OPENCODE_CMD",
            default_model="default",
            model_env_var="LUTHIER_OPENCODE_MODEL",
            runner=runner,
        )

    def build_command(
        self,
        prompt,
        schema_path: Path,
        output_path: Path,
    ) -> list[str]:
        del schema_path, output_path
        return self.resolve_command_prefix() + [
            "run",
            "--format",
            "json",
            "--model",
            self.resolve_model(),
            self.render_prompt(prompt),
        ]

    def build_stdin(self, prompt) -> str | None:
        del prompt
        return None

    def output_mode(self) -> str:
        return "json-events-stdout"

    def parse_payload(self, *, stdout: str, stderr: str, output_path: Path) -> dict[str, Any]:
        del stderr, output_path
        stdout = stdout.strip()
        if not stdout:
            raise RuntimeError(
                "opencode adapter returned empty stdout. Expected JSON events on stdout."
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if len(lines) == 1 and lines[0].startswith("{"):
            payload = self._load_json(lines[0])
            if "findings" in payload:
                return payload

        last_text = ""
        for line in lines:
            event = self._load_json(line)
            if "findings" in event:
                return event

            if event.get("type") in {"message", "assistant_message", "response.completed"}:
                text = self._extract_text(event)
                if text:
                    last_text = text

        if last_text:
            return self._load_json(last_text)

        raise RuntimeError(
            "opencode adapter did not emit a structured JSON result in its event stream."
        )

    def _extract_text(self, event: dict[str, Any]) -> str:
        for key in ("text", "content", "message"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if isinstance(text, str) and text.strip():
                            return text.strip()
        return ""
