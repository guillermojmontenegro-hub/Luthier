from __future__ import annotations

import json
from pathlib import Path

from core.models import EvaluationProfile
from core.policies import is_known_policy_pack, resolve_policy_selection, validate_policy_registry
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
        requested_policy_pack="generic-agentic",
        policy_pack="generic-agentic",
        policy_resolution="default",
        agent_runtime="generic",
        model_family="generic",
        llm_provider="none",
    )


def load_profile(
    profile_path: str | None,
    root_path: str,
    policy_pack: str | None = None,
    agent_runtime: str | None = None,
    model_family: str | None = None,
    llm_provider: str | None = None,
) -> EvaluationProfile:
    validate_policy_registry()

    if not profile_path:
        profile = default_profile(root_path)
        profile.agent_runtime = agent_runtime or profile.agent_runtime
        profile.model_family = model_family or profile.model_family
        profile.llm_provider = llm_provider or profile.llm_provider
        if policy_pack and policy_pack.lower() != "auto" and not is_known_policy_pack(policy_pack):
            raise ValueError(f"Unknown policy pack: {policy_pack}")
        requested_policy_pack, resolved_policy_pack, policy_resolution = resolve_policy_selection(
            policy_pack,
            profile.policy_pack,
            profile.model_family,
            profile.agent_runtime,
        )
        profile.requested_policy_pack = requested_policy_pack
        profile.policy_pack = resolved_policy_pack
        profile.policy_resolution = policy_resolution
        validate_profile_payload(profile.to_dict())
        return profile

    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    resolved_agent_runtime = payload.get("agent_runtime", "generic")
    resolved_model_family = payload.get("model_family", "generic")
    if agent_runtime:
        resolved_agent_runtime = agent_runtime
    if model_family:
        resolved_model_family = model_family
    if policy_pack and policy_pack.lower() != "auto" and not is_known_policy_pack(policy_pack):
        raise ValueError(f"Unknown policy pack: {policy_pack}")
    requested_policy_pack, resolved_policy_pack, policy_resolution = resolve_policy_selection(
        policy_pack,
        payload.get("policy_pack"),
        resolved_model_family,
        resolved_agent_runtime,
    )

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
        requested_policy_pack=requested_policy_pack,
        policy_pack=resolved_policy_pack,
        policy_resolution=policy_resolution,
        agent_runtime=resolved_agent_runtime,
        model_family=resolved_model_family,
        llm_provider=llm_provider or payload.get("llm_provider", "none"),
    )
    validate_profile_payload(profile.to_dict())
    return profile
