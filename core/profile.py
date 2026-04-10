from __future__ import annotations

import json
from pathlib import Path

from core.models import EvaluationProfile


def default_profile(root_path: str) -> EvaluationProfile:
    return EvaluationProfile(
        version="1.0",
        name="default-local",
        root_path=root_path,
        output_formats=["json", "md", "txt"],
        language="es",
        shell="bash",
        operating_system="linux",
        network_access="enabled",
        approval_mode="on-request",
        runtime_agnostic=True,
        policy_pack="generic-agentic",
        agent_runtime="generic",
        model_family="generic",
    )


def load_profile(profile_path: str | None, root_path: str) -> EvaluationProfile:
    if not profile_path:
        return default_profile(root_path)

    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    return EvaluationProfile(
        version=payload.get("version", "1.0"),
        name=payload.get("name", "default-local"),
        root_path=payload.get("root_path", root_path),
        output_formats=payload.get("output_formats", ["json", "md", "txt"]),
        language=payload.get("language", "es"),
        shell=payload.get("shell", "bash"),
        operating_system=payload.get("operating_system", "linux"),
        network_access=payload.get("network_access", "enabled"),
        approval_mode=payload.get("approval_mode", "on-request"),
        runtime_agnostic=payload.get("runtime_agnostic", True),
        policy_pack=payload.get("policy_pack", "generic-agentic"),
        agent_runtime=payload.get("agent_runtime", "generic"),
        model_family=payload.get("model_family", "generic"),
    )
