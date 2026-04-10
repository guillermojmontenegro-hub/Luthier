from __future__ import annotations

from policies.claude_4x import POLICY_PACK as CLAUDE_4X_POLICY
from policies.generic_agentic import POLICY_PACK as GENERIC_AGENTIC_POLICY
from policies.openai_gpt5 import POLICY_PACK as OPENAI_GPT5_POLICY

POLICY_REGISTRY = {
    GENERIC_AGENTIC_POLICY["name"]: GENERIC_AGENTIC_POLICY,
    OPENAI_GPT5_POLICY["name"]: OPENAI_GPT5_POLICY,
    CLAUDE_4X_POLICY["name"]: CLAUDE_4X_POLICY,
}


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
    return GENERIC_AGENTIC_POLICY["name"]


def resolve_policy_pack(
    explicit_policy_pack: str | None,
    model_family: str,
    agent_runtime: str,
) -> str:
    if explicit_policy_pack and explicit_policy_pack.lower() != "auto":
        return explicit_policy_pack
    return infer_policy_pack(model_family, agent_runtime)
