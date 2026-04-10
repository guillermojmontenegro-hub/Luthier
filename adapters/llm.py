from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

ALLOWED_SEVERITIES = {"low", "medium", "high"}


@dataclass(slots=True)
class StructuredPrompt:
    prompt_type: str
    version: str
    instructions: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LLMFinding:
    code: str
    severity: str
    message: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LLMEvaluationResult:
    prompt_type: str
    findings: list[LLMFinding]
    summary: str = ""
    provider: str = "mock"
    model: str = "mock"
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [item.to_dict() for item in self.findings]
        return payload


class LLMAdapter(Protocol):
    def evaluate(self, prompt: StructuredPrompt) -> LLMEvaluationResult:
        """Return structured findings without coupling the core to a provider."""


def parse_llm_evaluation(payload: dict[str, Any], prompt_type: str) -> LLMEvaluationResult:
    findings_payload = payload.get("findings", [])
    if not isinstance(findings_payload, list):
        raise ValueError("LLM evaluation payload must include a `findings` array.")

    findings: list[LLMFinding] = []
    for index, item in enumerate(findings_payload):
        if not isinstance(item, dict):
            raise ValueError(f"LLM finding at index {index} must be an object.")

        severity = item.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"LLM finding at index {index} has invalid severity {severity!r}. "
                f"Expected one of {sorted(ALLOWED_SEVERITIES)}."
            )

        code = item.get("code")
        message = item.get("message")
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"LLM finding at index {index} is missing a valid `code`.")
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f"LLM finding at index {index} is missing a valid `message`.")

        evidence = item.get("evidence", [])
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list) or any(not isinstance(line, str) for line in evidence):
            raise ValueError(
                f"LLM finding at index {index} must use a string array for `evidence`."
            )

        recommendation = item.get("recommendation", "")
        if recommendation is None:
            recommendation = ""
        if not isinstance(recommendation, str):
            raise ValueError(
                f"LLM finding at index {index} must use a string for `recommendation`."
            )

        findings.append(
            LLMFinding(
                code=code.strip(),
                severity=severity,
                message=message.strip(),
                evidence=evidence,
                recommendation=recommendation.strip(),
            )
        )

    summary = payload.get("summary", "")
    if summary is None:
        summary = ""
    if not isinstance(summary, str):
        raise ValueError("LLM evaluation payload must use a string for `summary`.")

    provider = payload.get("provider", "mock")
    model = payload.get("model", "mock")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("LLM evaluation payload must use a non-empty string for `provider`.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("LLM evaluation payload must use a non-empty string for `model`.")

    return LLMEvaluationResult(
        prompt_type=prompt_type,
        findings=findings,
        summary=summary.strip(),
        provider=provider.strip(),
        model=model.strip(),
        raw_response=payload,
    )
