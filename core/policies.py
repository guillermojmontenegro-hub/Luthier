from __future__ import annotations

from core.naming import is_canonical_policy_pack_name
from policies.claude_4x import POLICY_PACK as CLAUDE_4X_POLICY
from policies.gemini_25 import POLICY_PACK as GEMINI_25_POLICY
from policies.generic_agentic import POLICY_PACK as GENERIC_AGENTIC_POLICY
from policies.openai_gpt5 import POLICY_PACK as OPENAI_GPT5_POLICY
from policies.qwen_3 import POLICY_PACK as QWEN_3_POLICY

POLICY_REGISTRY = {
    GENERIC_AGENTIC_POLICY["name"]: GENERIC_AGENTIC_POLICY,
    OPENAI_GPT5_POLICY["name"]: OPENAI_GPT5_POLICY,
    CLAUDE_4X_POLICY["name"]: CLAUDE_4X_POLICY,
    GEMINI_25_POLICY["name"]: GEMINI_25_POLICY,
    QWEN_3_POLICY["name"]: QWEN_3_POLICY,
}


def get_policy_pack(name: str) -> dict:
    return POLICY_REGISTRY.get(name, GENERIC_AGENTIC_POLICY)


def is_known_policy_pack(name: str) -> bool:
    return name in POLICY_REGISTRY


def list_policy_packs() -> list[str]:
    return sorted(POLICY_REGISTRY)


def validate_policy_registry() -> None:
    for policy_name in POLICY_REGISTRY:
        if not is_canonical_policy_pack_name(policy_name):
            raise ValueError(
                f"Policy pack '{policy_name}' should use lowercase kebab-case identifiers."
            )


def get_policy_rules_version(name: str) -> str:
    policy = get_policy_pack(name)
    return str(policy.get("rules_version", policy.get("version", "1.0")))


def get_policy_prompt_version(name: str) -> str:
    policy = get_policy_pack(name)
    return str(policy.get("prompt_version", policy.get("version", "1.0")))


def get_policy_prompt_suffix(name: str, prompt_type: str) -> str:
    policy = get_policy_pack(name)
    suffixes = policy.get("prompt_suffixes", {})
    return str(suffixes.get(prompt_type, "")).strip()


def infer_policy_pack(model_family: str, agent_runtime: str) -> str:
    normalized_model = model_family.strip().lower()
    normalized_runtime = agent_runtime.strip().lower()

    if (
        any(marker in normalized_model for marker in ("gpt", "openai"))
        or "codex" in normalized_runtime
    ):
        return OPENAI_GPT5_POLICY["name"]
    if "claude" in normalized_model or "claude" in normalized_runtime:
        return CLAUDE_4X_POLICY["name"]
    if "gemini" in normalized_model or "gemini" in normalized_runtime:
        return GEMINI_25_POLICY["name"]
    if "qwen" in normalized_model or "qwen" in normalized_runtime:
        return QWEN_3_POLICY["name"]
    return GENERIC_AGENTIC_POLICY["name"]


def resolve_policy_pack(
    explicit_policy_pack: str | None,
    model_family: str,
    agent_runtime: str,
) -> str:
    if explicit_policy_pack and explicit_policy_pack.lower() != "auto":
        return explicit_policy_pack
    return infer_policy_pack(model_family, agent_runtime)


def resolve_policy_selection(
    requested_policy_pack: str | None,
    fallback_policy_pack: str | None,
    model_family: str,
    agent_runtime: str,
) -> tuple[str, str, str]:
    if requested_policy_pack:
        if requested_policy_pack.lower() == "auto":
            return (
                "auto",
                infer_policy_pack(model_family, agent_runtime),
                "inferred",
            )
        return requested_policy_pack, requested_policy_pack, "explicit"

    if fallback_policy_pack:
        return fallback_policy_pack, fallback_policy_pack, "default"

    inferred_policy = infer_policy_pack(model_family, agent_runtime)
    return "auto", inferred_policy, "inferred"
