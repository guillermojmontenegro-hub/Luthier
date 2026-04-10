from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.llm import parse_llm_evaluation
from adapters.mock import MockLLMAdapter
from core.conflict_report import build_report
from core.discovery import discover_skills
from core.profile import default_profile
from prompts.structured import (
    build_report_synthesis_prompt,
    build_skill_audit_prompt,
    build_skill_compare_prompt,
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
