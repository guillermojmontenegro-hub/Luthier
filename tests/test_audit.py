from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli.main import main
from core.audit import audit_path
from core.conflict_report import build_report
from core.conflicts import detect_conflicts
from core.discovery import discover_skills
from core.metrics import compute_metrics
from core.parser import extract_examples, extract_restriction_lines, extract_usage_lines
from core.profile import default_profile, load_profile
from core.rules import evaluate_rules
from core.schema_validation import validate_report_payload

ROOT = Path(__file__).resolve().parent.parent


class AuditTests(unittest.TestCase):
    def test_audit_discovers_fixtures(self) -> None:
        report = audit_path(ROOT / "fixtures", default_profile(str(ROOT / "fixtures"))).to_dict()
        self.assertEqual(report["summary"]["skill_count"], 2)
        names = {item["skill"]["name"] for item in report["skills"]}
        self.assertEqual(names, {"simple_skill", "conflicting_skill"})

    def test_audit_flags_missing_reference(self) -> None:
        report = audit_path(
            ROOT / "fixtures" / "conflicting_skill", default_profile(str(ROOT))
        ).to_dict()
        findings = report["skills"][0]["findings"]
        codes = {item["code"] for item in findings}
        self.assertIn("broken-references", codes)

    def test_cli_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "audit",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json,md,txt",
                ]
            )
            self.assertEqual(code, 0)
            report_path = Path(tmp) / "report.json"
            self.assertTrue(report_path.exists())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["skill_count"], 2)
            validate_report_payload(payload)

    def test_parser_extracts_usage_restrictions_and_examples(self) -> None:
        content = (
            "# Demo Skill\n\n"
            "Use this skill when a repo needs cleanup.\n\n"
            "## Usage\n\n"
            "- Use it for small repositories.\n"
            "- Avoid it for production rollouts.\n\n"
            "## Rules\n\n"
            "- Always use `rg`.\n"
            "- Never rewrite unrelated files.\n\n"
            "## Examples\n\n"
            "Example: audit a single folder.\n"
            "- audit `docs/`\n"
        )

        self.assertEqual(
            extract_usage_lines(content),
            ["Use it for small repositories.", "Avoid it for production rollouts."],
        )
        self.assertEqual(
            extract_restriction_lines(content),
            ["Always use `rg`.", "Never rewrite unrelated files."],
        )
        self.assertEqual(
            extract_examples(content),
            ["audit a single folder.", "audit `docs/`"],
        )

    def test_discovery_merges_skill_and_agents_in_same_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dual_manifest_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Dual Manifest Skill\n\n"
                "Use this skill for audits.\n\n"
                "## Usage\n\n"
                "- Use it on repos.\n",
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text(
                "## Rules\n\n- Always use `rg`.\n\nSee `guide.md`.\n",
                encoding="utf-8",
            )
            (root / "guide.md").write_text("supporting guide\n", encoding="utf-8")

            skills = discover_skills(root.parent)

            self.assertEqual(len(skills), 1)
            skill = skills[0]
            self.assertEqual(skill.main_file, str(root / "SKILL.md"))
            self.assertEqual(len(skill.source_files), 2)
            self.assertIn("Use it on repos.", skill.usage_lines)
            self.assertIn("Always use `rg`.", skill.restriction_lines)
            self.assertTrue(any(ref.path == "guide.md" and ref.exists for ref in skill.references))
            self.assertGreater(skill.total_size_bytes, len(skill.content))

    def test_metrics_use_parsed_examples(self) -> None:
        skill = discover_skills(ROOT / "fixtures" / "simple_skill")[0]
        metrics = compute_metrics(skill)

        self.assertEqual(metrics.example_count, 1)
        self.assertGreater(metrics.total_chars, metrics.description_chars)

    def test_rules_flag_rigid_tooling_and_over_specified_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rigid_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Rigid Skill\n\n"
                "Use this skill to process repositories.\n\n"
                "## Steps\n\n"
                "- First read the repo.\n"
                "- Then inspect every directory.\n"
                "- Then list every file.\n"
                "- Then open the main docs.\n"
                "- Then run the audit.\n"
                "- Then rewrite the summary.\n"
                "- Then verify all outputs.\n"
                "- Finally publish the report.\n\n"
                "## Rules\n\n"
                "- Always use `python`.\n"
                "- Must use `rg`.\n"
                "- Never use `grep`.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            findings = evaluate_rules(skill, compute_metrics(skill), default_profile(str(root)))
            codes = {item.code for item in findings}

            self.assertIn("rigid-tooling-or-sequence", codes)
            self.assertIn("over-specified-workflow", codes)

    def test_rules_flag_duplicated_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "duplicated_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Duplicated Skill\n\n"
                "Use this skill for consistent audits.\n\n"
                "## Rules\n\n"
                "- Always use `rg` for search.\n"
                "- Always use `rg` for search.\n"
                "- Never rewrite unrelated files.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            findings = evaluate_rules(skill, compute_metrics(skill), default_profile(str(root)))
            codes = {item.code for item in findings}

            self.assertIn("duplicated-instructions", codes)

    def test_conflicts_detect_shell_and_os_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "bash_skill"
            right = root / "powershell_skill"
            left.mkdir()
            right.mkdir()
            (left / "SKILL.md").write_text(
                "# Bash Skill\n\n"
                "Use this skill for Linux work.\n\n"
                "## Rules\n\n"
                "- Always use bash.\n"
                "- Ask clarifying questions.\n",
                encoding="utf-8",
            )
            (right / "SKILL.md").write_text(
                "# PowerShell Skill\n\n"
                "Usa este skill para tareas en Windows.\n\n"
                "## Rules\n\n"
                "- Always use PowerShell.\n"
                "- Always use Windows paths.\n"
                "- Never ask follow-up questions.\n",
                encoding="utf-8",
            )

            conflicts = detect_conflicts(discover_skills(root))
            categories = {item.category for item in conflicts}
            self.assertIn("shell", categories)
            self.assertIn("confirmation-policy", categories)

    def test_conflicts_are_ranked_and_include_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "generic_overlap"
            right = root / "generic_overlap_two"
            left.mkdir()
            right.mkdir()
            shared_content = (
                "Use this general skill for many things across repositories.\n\n"
                "## Steps\n\n"
                "- Read the repository.\n"
                "- Inspect the documentation.\n"
                "- Compare the same workflows.\n"
                "- Summarize the same findings.\n\n"
                "## Examples\n\n"
                "Example: audit a folder.\n"
            )
            (left / "SKILL.md").write_text(
                f"# Generic Overlap\n\n{shared_content}", encoding="utf-8"
            )
            (right / "SKILL.md").write_text(
                f"# Generic Overlap Two\n\n{shared_content}", encoding="utf-8"
            )

            conflicts = detect_conflicts(discover_skills(root))

            self.assertGreaterEqual(len(conflicts), 2)
            self.assertGreaterEqual(conflicts[0].priority, conflicts[-1].priority)
            self.assertTrue(conflicts[0].recommendation)
            categories = {item.category for item in conflicts}
            self.assertIn("overlap", categories)
            self.assertIn("misleading-discovery", categories)

    def test_conflicts_detect_tone_and_role_mismatch_when_skills_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = root / "supportive_builder"
            reviewer = root / "strict_reviewer"
            builder.mkdir()
            reviewer.mkdir()
            shared_usage = (
                "Use this skill for repository changes and implementation tasks.\n\n"
                "## Usage\n\n"
                "- Work on code changes in the repository.\n"
                "- Summarize the same repository findings.\n\n"
                "## Guidance\n\n"
            )
            (builder / "SKILL.md").write_text(
                "# Supportive Builder\n\n"
                f"{shared_usage}"
                "Be warm, encouraging, supportive, and collaborative.\n"
                "Act as a coding agent and make code changes directly.\n",
                encoding="utf-8",
            )
            (reviewer / "SKILL.md").write_text(
                "# Strict Reviewer\n\n"
                f"{shared_usage}"
                "Be blunt, strict, and critical when you communicate findings.\n"
                "Default to a code review mindset and prioritise identifying bugs.\n",
                encoding="utf-8",
            )

            conflicts = detect_conflicts(discover_skills(root))

            tone_role_conflicts = [item for item in conflicts if item.category == "tone-role"]
            self.assertEqual(len(tone_role_conflicts), 1)
            self.assertEqual(tone_role_conflicts[0].severity, "medium")
            self.assertTrue(any("tone:" in line for line in tone_role_conflicts[0].evidence))
            self.assertTrue(any("role:" in line for line in tone_role_conflicts[0].evidence))

    def test_conflicts_report_can_filter_explicit_skill_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bash_skill = root / "bash_skill"
            powershell_skill = root / "powershell_skill"
            neutral_skill = root / "neutral_skill"
            bash_skill.mkdir()
            powershell_skill.mkdir()
            neutral_skill.mkdir()
            (bash_skill / "SKILL.md").write_text(
                "# Bash Skill\n\n"
                "Use this skill for Linux work.\n\n"
                "## Rules\n\n"
                "- Always use bash.\n",
                encoding="utf-8",
            )
            (powershell_skill / "SKILL.md").write_text(
                "# PowerShell Skill\n\n"
                "Use this skill for Windows work.\n\n"
                "## Rules\n\n"
                "- Always use PowerShell.\n",
                encoding="utf-8",
            )
            (neutral_skill / "SKILL.md").write_text(
                "# Neutral Skill\n\nUse this skill for summaries.\n",
                encoding="utf-8",
            )

            report = build_report(
                root,
                default_profile(str(root)),
                include_conflicts=True,
                selected_skills={"bash_skill", "powershell_skill"},
            ).to_dict()

            audited_names = {item["skill"]["name"] for item in report["skills"]}
            self.assertEqual(audited_names, {"bash_skill", "powershell_skill"})
            self.assertGreaterEqual(report["summary"]["highest_conflict_priority"], 1)
            self.assertTrue(
                all(
                    "neutral_skill" not in (item["left_skill"], item["right_skill"])
                    for item in report["conflicts"]
                )
            )

    def test_conflicts_report_can_filter_by_folder_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unix_group = root / "unix"
            windows_group = root / "windows"
            docs_group = root / "docs"
            for folder in (unix_group, windows_group, docs_group):
                folder.mkdir()

            (unix_group / "bash_skill").mkdir()
            (windows_group / "powershell_skill").mkdir()
            (docs_group / "neutral_skill").mkdir()

            (unix_group / "bash_skill" / "SKILL.md").write_text(
                "# Bash Skill\n\n"
                "Use this skill for Linux work.\n\n"
                "## Rules\n\n"
                "- Always use bash.\n",
                encoding="utf-8",
            )
            (windows_group / "powershell_skill" / "SKILL.md").write_text(
                "# PowerShell Skill\n\n"
                "Use this skill for Windows work.\n\n"
                "## Rules\n\n"
                "- Always use PowerShell.\n",
                encoding="utf-8",
            )
            (docs_group / "neutral_skill" / "SKILL.md").write_text(
                "# Neutral Skill\n\nUse this skill for summaries.\n",
                encoding="utf-8",
            )

            report = build_report(
                root,
                default_profile(str(root)),
                include_conflicts=True,
                selected_folders={"unix", "windows"},
            ).to_dict()

            audited_names = {item["skill"]["name"] for item in report["skills"]}
            self.assertEqual(audited_names, {"bash_skill", "powershell_skill"})
            self.assertTrue(
                all(
                    "neutral_skill" not in (item["left_skill"], item["right_skill"])
                    for item in report["conflicts"]
                )
            )

    def test_conflicts_cli_writes_conflict_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "conflicts",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json,md,txt",
                ]
            )
            self.assertEqual(code, 0)
            report_path = Path(tmp) / "report.json"
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("conflict_count", payload["summary"])

    def test_conflicts_cli_can_fail_on_conflict_priority_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            (root / "bash_skill").mkdir(parents=True)
            (root / "powershell_skill").mkdir(parents=True)
            (root / "bash_skill" / "SKILL.md").write_text(
                "# Bash Skill\n\n"
                "Use this skill for Linux work.\n\n"
                "## Rules\n\n"
                "- Always use bash.\n",
                encoding="utf-8",
            )
            (root / "powershell_skill" / "SKILL.md").write_text(
                "# PowerShell Skill\n\n"
                "Use this skill for Windows work.\n\n"
                "## Rules\n\n"
                "- Always use PowerShell.\n",
                encoding="utf-8",
            )

            code = main(
                [
                    "conflicts",
                    str(root),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json",
                    "--fail-on-conflict-priority",
                    "1",
                ]
            )

            self.assertEqual(code, 3)

    def test_conflicts_cli_filters_selected_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            root.mkdir()
            for name, rule in (
                ("bash_skill", "- Always use bash.\n"),
                ("powershell_skill", "- Always use PowerShell.\n"),
                ("neutral_skill", "- Write a short summary.\n"),
            ):
                folder = root / name
                folder.mkdir()
                (folder / "SKILL.md").write_text(
                    f"# {name}\n\nUse this skill for repository work.\n\n## Rules\n\n{rule}",
                    encoding="utf-8",
                )

            output_dir = Path(tmp) / "out"
            code = main(
                [
                    "conflicts",
                    str(root),
                    "--skills",
                    "bash_skill,powershell_skill",
                    "--output-dir",
                    str(output_dir),
                    "--format",
                    "json",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            audited_names = {item["skill"]["name"] for item in payload["skills"]}
            self.assertEqual(audited_names, {"bash_skill", "powershell_skill"})

    def test_conflicts_cli_filters_selected_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            for group_name, skill_name, rule in (
                ("unix", "bash_skill", "- Always use bash.\n"),
                ("windows", "powershell_skill", "- Always use PowerShell.\n"),
                ("docs", "neutral_skill", "- Write a short summary.\n"),
            ):
                folder = root / group_name / skill_name
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text(
                    f"# {skill_name}\n\nUse this skill for repository work.\n\n## Rules\n\n{rule}",
                    encoding="utf-8",
                )

            output_dir = Path(tmp) / "out"
            code = main(
                [
                    "conflicts",
                    str(root),
                    "--folders",
                    "unix,windows",
                    "--output-dir",
                    str(output_dir),
                    "--format",
                    "json",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
            audited_names = {item["skill"]["name"] for item in payload["skills"]}
            self.assertEqual(audited_names, {"bash_skill", "powershell_skill"})

    def test_report_cli_generates_full_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "report",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json,md",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertIn("conflicts", payload)
            self.assertTrue((Path(tmp) / "report.md").exists())

    def test_report_cli_can_fail_on_risk_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "report",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json",
                    "--fail-on-threshold",
                    "1",
                ]
            )

            self.assertEqual(code, 2)

    def test_profile_overrides_can_infer_policy_pack(self) -> None:
        profile = load_profile(
            None,
            root_path=str(ROOT),
            policy_pack="auto",
            agent_runtime="codex",
            model_family="gpt-5",
        )

        self.assertEqual(profile.agent_runtime, "codex")
        self.assertEqual(profile.model_family, "gpt-5")
        self.assertEqual(profile.policy_pack, "openai-gpt5")

    def test_profile_file_without_policy_uses_inferred_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "name": "claude-profile",
                        "agent_runtime": "claude-code",
                        "model_family": "claude-4.1",
                    }
                ),
                encoding="utf-8",
            )

            profile = load_profile(str(profile_path), root_path=str(ROOT))

            self.assertEqual(profile.policy_pack, "claude-4x")

    def test_profile_validation_rejects_invalid_output_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "name": "invalid-profile",
                        "output_formats": ["json", "yaml"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_profile(str(profile_path), root_path=str(ROOT))


if __name__ == "__main__":
    unittest.main()
