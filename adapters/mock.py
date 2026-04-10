from __future__ import annotations

from collections.abc import Callable
from typing import Any

from adapters.llm import LLMEvaluationResult, StructuredPrompt, parse_llm_evaluation


class MockLLMAdapter:
    def __init__(
        self,
        responder: Callable[[StructuredPrompt], dict[str, Any]] | None = None,
    ) -> None:
        self._responder = responder or self._default_response

    def evaluate(self, prompt: StructuredPrompt) -> LLMEvaluationResult:
        payload = self._responder(prompt)
        return parse_llm_evaluation(payload, prompt.prompt_type)

    @staticmethod
    def _default_response(prompt: StructuredPrompt) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        summary = "No additional LLM findings."

        if prompt.prompt_type == "skill-audit":
            description = str(prompt.payload.get("description", "")).strip()
            if not description:
                findings.append(
                    {
                        "code": "llm-missing-scope",
                        "severity": "medium",
                        "message": "The skill opening does not clearly explain its intended scope.",
                        "evidence": ["description=(empty)"],
                        "recommendation": (
                            "Add a short opening paragraph describing when the "
                            "skill should trigger."
                        ),
                    }
                )
                summary = "The skill needs a clearer opening scope."
        elif prompt.prompt_type == "skill-compare":
            left_name = str(prompt.payload.get("left_skill", "")).strip()
            right_name = str(prompt.payload.get("right_skill", "")).strip()
            left_description = str(prompt.payload.get("left_description", "")).strip().lower()
            right_description = str(prompt.payload.get("right_description", "")).strip().lower()
            if left_description and left_description == right_description:
                findings.append(
                    {
                        "code": "llm-semantic-overlap",
                        "severity": "medium",
                        "message": "Both skills appear to communicate the same responsibility.",
                        "evidence": [f"{left_name} description matches {right_name} description"],
                        "recommendation": (
                            "Rename or split the skills so each one has a sharper "
                            "trigger."
                        ),
                    }
                )
                summary = "The skills appear semantically redundant."
        elif prompt.prompt_type == "report-synthesis":
            finding_count = int(prompt.payload.get("finding_count", 0))
            conflict_count = int(prompt.payload.get("conflict_count", 0))
            summary = (
                f"Run summary: {finding_count} findings and {conflict_count} conflicts "
                "were provided to the synthesis adapter."
            )

        return {
            "provider": "mock",
            "model": "mock-static-v1",
            "summary": summary,
            "findings": findings,
        }
