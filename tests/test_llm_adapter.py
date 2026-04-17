from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters import create_adapter
from adapters.claude_code import ClaudeCodeLLMAdapter
from adapters.codex import CodexLLMAdapter
from adapters.command import CommandLLMAdapter
from adapters.llm import parse_llm_evaluation
from adapters.mock import MockLLMAdapter
from adapters.opencode import OpenCodeLLMAdapter
from core.conflict_report import build_report
from core.discovery import discover_skills
from core.profile import default_profile
from prompts.structured import (
    build_report_synthesis_prompt,
    build_report_synthesis_prompt_for_policy,
    build_skill_audit_prompt,
    build_skill_audit_prompt_for_policy,
    build_skill_compare_prompt,
    build_skill_compare_prompt_for_policy,
)

ROOT = Path(__file__).resolve().parent.parent


class LLMAdapterTests(unittest.TestCase):
    def test_parse_llm_evaluation_validates_findings_shape(self) -> None:
        result = parse_llm_evaluation(
            {
                "provider": "mock",
                "model": "mock-v1",
                "summary": "ok",
                "findings": [
                    {
                        "code": "llm-test",
                        "severity": "low",
                        "message": "Structured result.",
                        "evidence": ["line one"],
                        "recommendation": "Keep it concise.",
                    }
                ],
            },
            "skill-audit",
        )

        self.assertEqual(result.prompt_type, "skill-audit")
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, "low")

    def test_parse_llm_evaluation_rejects_invalid_severity(self) -> None:
        with self.assertRaises(ValueError):
            parse_llm_evaluation(
                {
                    "findings": [
                        {
                            "code": "llm-test",
                            "severity": "critical",
                            "message": "Bad severity.",
                        }
                    ]
                },
                "skill-audit",
            )

    def test_mock_adapter_returns_finding_for_empty_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "empty_description_skill"
            root.mkdir()
            (root / "SKILL.md").write_text("# Empty Description Skill\n", encoding="utf-8")

            skill = discover_skills(root)[0]
            adapter = MockLLMAdapter()
            result = adapter.evaluate(build_skill_audit_prompt(skill))

            self.assertEqual(result.provider, "mock")
            self.assertEqual(result.prompt_type, "skill-audit")
            self.assertEqual(result.findings[0].code, "llm-missing-scope")

    def test_mock_adapter_compares_two_skills_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left_skill"
            right = root / "right_skill"
            left.mkdir()
            right.mkdir()
            content = "# Skill\n\nUse this skill for repository triage.\n"
            (left / "SKILL.md").write_text(content, encoding="utf-8")
            (right / "SKILL.md").write_text(content, encoding="utf-8")

            left_skill, right_skill = discover_skills(root)
            adapter = MockLLMAdapter()
            result = adapter.evaluate(build_skill_compare_prompt(left_skill, right_skill))

            self.assertEqual(result.prompt_type, "skill-compare")
            self.assertEqual(result.findings[0].code, "llm-semantic-overlap")

    def test_mock_adapter_synthesizes_report_prompt(self) -> None:
        report = build_report(ROOT / "fixtures", default_profile(str(ROOT)), include_conflicts=True)
        adapter = MockLLMAdapter()
        result = adapter.evaluate(build_report_synthesis_prompt(report))

        self.assertEqual(result.prompt_type, "report-synthesis")
        self.assertIn("findings", result.summary)
        self.assertEqual(result.findings, [])

    def test_policy_specific_prompt_versions_are_embedded(self) -> None:
        skill = discover_skills(ROOT / "fixtures" / "simple_skill")[0]
        report = build_report(ROOT / "fixtures", default_profile(str(ROOT)), include_conflicts=True)

        audit_prompt = build_skill_audit_prompt_for_policy(skill, "openai-gpt5")
        compare_prompt = build_skill_compare_prompt_for_policy(skill, skill, "claude-4x")
        synthesis_prompt = build_report_synthesis_prompt_for_policy(report, "openai-gpt5")

        self.assertEqual(audit_prompt.version, "openai-gpt5@1.1")
        self.assertIn("freshness-sensitive", audit_prompt.instructions)
        self.assertEqual(compare_prompt.version, "claude-4x@1.1")
        self.assertIn("ownership", compare_prompt.instructions)
        self.assertEqual(synthesis_prompt.payload["policy_pack"], "openai-gpt5")

    def test_create_adapter_supports_real_provider_names(self) -> None:
        self.assertIsInstance(create_adapter("codex"), CodexLLMAdapter)
        self.assertIsInstance(create_adapter("claude-code"), ClaudeCodeLLMAdapter)
        self.assertIsInstance(create_adapter("opencode"), OpenCodeLLMAdapter)

    def test_command_adapter_uses_environment_override(self) -> None:
        adapter = CommandLLMAdapter(
            provider="test",
            default_command="default-llm",
            command_env_var="LUTHIER_TEST_CMD",
        )

        with patch.dict(os.environ, {"LUTHIER_TEST_CMD": "custom-llm --json"}, clear=False):
            self.assertEqual(adapter.resolve_command(), ["custom-llm", "--json"])

    def test_command_adapter_parses_json_stdout(self) -> None:
        calls: list[dict[str, object]] = []

        def runner(command: list[str], **kwargs: object) -> object:
            calls.append({"command": command, **kwargs})
            return type(
                "Completed",
                (),
                {
                    "stdout": json.dumps(
                        {
                            "provider": "codex",
                            "model": "gpt-5",
                            "summary": "ok",
                            "findings": [],
                        }
                    )
                },
            )()

        adapter = CommandLLMAdapter(
            provider="codex",
            default_command="codex-llm",
            command_env_var="LUTHIER_CODEX_CMD",
            runner=runner,
        )

        result = adapter.evaluate(
            build_skill_audit_prompt(discover_skills(ROOT / "fixtures" / "simple_skill")[0])
        )

        self.assertEqual(result.provider, "codex")
        self.assertEqual(result.model, "gpt-5")
        self.assertEqual(calls[0]["command"], ["codex-llm"])
        self.assertTrue(isinstance(calls[0]["input"], str))

    def test_command_adapter_raises_clear_error_on_missing_executable(self) -> None:
        def runner(command: list[str], **kwargs: object) -> object:
            raise FileNotFoundError("missing")

        adapter = CommandLLMAdapter(
            provider="codex",
            default_command="codex-llm",
            command_env_var="LUTHIER_CODEX_CMD",
            runner=runner,
        )

        with self.assertRaises(RuntimeError) as exc:
            adapter.evaluate(
                build_skill_audit_prompt(discover_skills(ROOT / "fixtures" / "simple_skill")[0])
            )

        self.assertIn("LUTHIER_CODEX_CMD", str(exc.exception))
