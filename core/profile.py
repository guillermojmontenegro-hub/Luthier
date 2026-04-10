from __future__ import annotations

import json
from pathlib import Path

from core.models import EvaluationProfile
from core.policies import resolve_policy_pack
from core.schema_validation import validate_profile_payload


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


def load_profile(
    profile_path: str | None,
    root_path: str,
    policy_pack: str | None = None,
    agent_runtime: str | None = None,
    model_family: str | None = None,
) -> EvaluationProfile:
    if not profile_path:
        profile = default_profile(root_path)
        profile.agent_runtime = agent_runtime or profile.agent_runtime
        profile.model_family = model_family or profile.model_family
        profile.policy_pack = resolve_policy_pack(
            policy_pack or profile.policy_pack,
            profile.model_family,
            profile.agent_runtime,
        )
        validate_profile_payload(profile.to_dict())
        return profile

    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    resolved_agent_runtime = payload.get("agent_runtime", "generic")
    resolved_model_family = payload.get("model_family", "generic")
    if agent_runtime:
        resolved_agent_runtime = agent_runtime
    if model_family:
        resolved_model_family = model_family

    profile = EvaluationProfile(
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
        policy_pack=resolve_policy_pack(
            policy_pack or payload.get("policy_pack"),
            resolved_model_family,
            resolved_agent_runtime,
        ),
        agent_runtime=resolved_agent_runtime,
        model_family=resolved_model_family,
    )
    validate_profile_payload(profile.to_dict())
    return profile
