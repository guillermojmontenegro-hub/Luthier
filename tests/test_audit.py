from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli.main import main
from core.audit import audit_path
from core.conflict_report import build_report
from core.conflicts import detect_conflicts
from core.diffing import build_diff
from core.discovery import discover_skills
from core.metrics import compute_metrics
from core.parser import (
    extract_examples,
    extract_restriction_lines,
    extract_usage_lines,
)
from core.profile import default_profile, load_profile
from core.rules import evaluate_rules
from core.schema_validation import validate_report_payload
from core.scoring import compute_scores

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

    def test_cli_can_enable_mock_llm_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "empty_description_skill"
            skill_root.mkdir()
            (skill_root / "SKILL.md").write_text("# Empty Description Skill\n", encoding="utf-8")

            code = main(
                [
                    "audit",
                    str(skill_root),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json",
                    "--llm",
                    "mock",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["llm_provider"], "mock")
            self.assertGreaterEqual(payload["summary"]["llm_finding_count"], 1)
            llm_sources = {
                finding["source"]
                for skill in payload["skills"]
                for finding in skill["findings"]
                if finding["code"].startswith("llm-")
            }
            self.assertEqual(llm_sources, {"llm"})

    def test_report_with_mock_llm_adds_conflicts_and_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left_skill"
            right = root / "right_skill"
            left.mkdir()
            right.mkdir()
            content = "# Skill\n\nUse this skill for repository triage.\n"
            (left / "SKILL.md").write_text(content, encoding="utf-8")
            (right / "SKILL.md").write_text(content, encoding="utf-8")

            code = main(
                [
                    "report",
                    str(root),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json,md,txt",
                    "--llm",
                    "mock",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["llm_provider"], "mock")
            self.assertEqual(payload["summary"]["llm_conflict_count"], 1)
            self.assertTrue(payload["summary"]["llm_summary"])
            llm_conflicts = [item for item in payload["conflicts"] if item["source"] == "llm"]
            self.assertEqual(len(llm_conflicts), 1)
            self.assertEqual(llm_conflicts[0]["category"], "llm-semantic-overlap")

            report_md = (Path(tmp) / "report.md").read_text(encoding="utf-8")
            self.assertIn("## LLM Synthesis", report_md)
            self.assertIn("[medium][llm] llm-semantic-overlap", report_md)

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
            self.assertTrue(conflicts[0].cluster_id)
            self.assertGreaterEqual(conflicts[0].cluster_size, 2)
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

    def test_conflicts_reduce_pairwise_noise_for_large_collections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(6):
                skill_dir = root / f"repo_overlap_{index}"
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    "# Repo Overlap\n\n"
                    "Use this general skill for many things across repositories.\n\n"
                    "## Steps\n\n"
                    "- Read the repository.\n"
                    "- Inspect the documentation.\n"
                    "- Compare the same workflows.\n"
                    "- Summarize the same findings.\n",
                    encoding="utf-8",
                )

            for index in range(3):
                skill_dir = root / f"isolated_{index}"
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    f"# Isolated {index}\n\n"
                    f"Use this skill for unrelated domain {index}.\n\n"
                    "## Rules\n\n"
                    "- Write a concise note.\n",
                    encoding="utf-8",
                )

            report = build_report(
                root,
                default_profile(str(root)),
                include_conflicts=True,
            ).to_dict()

            summary = report["summary"]
            self.assertEqual(summary["conflict_pairs_total"], 36)
            self.assertGreater(summary["conflict_pairs_skipped"], 0)
            self.assertLess(summary["conflict_pairs_compared"], summary["conflict_pairs_total"])
            self.assertGreaterEqual(summary["conflict_cluster_count"], 2)
            self.assertTrue(
                all(
                    not (
                        conflict["left_skill"].startswith("repo_overlap_")
                        and conflict["right_skill"].startswith("isolated_")
                    )
                    for conflict in report["conflicts"]
                )
            )

    def test_conflicts_detect_semantic_overlap_with_normalized_intent_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "docs_cleanup"
            right = root / "repo_guidance_review"
            left.mkdir()
            right.mkdir()
            (left / "SKILL.md").write_text(
                "# Docs Cleanup\n\n"
                "Use this skill for repository cleanup and documentation review.\n\n"
                "## Usage\n\n"
                "- Tidy outdated guides.\n"
                "- Summarize documentation issues.\n",
                encoding="utf-8",
            )
            (right / "SKILL.md").write_text(
                "# Repo Guidance Review\n\n"
                "Use this skill for project guidance triage and README audit.\n\n"
                "## Usage\n\n"
                "- Review stale docs.\n"
                "- Write a summary of repo problems.\n",
                encoding="utf-8",
            )

            conflicts = detect_conflicts(discover_skills(root))

            overlap_conflicts = [item for item in conflicts if item.category == "overlap"]
            self.assertEqual(len(overlap_conflicts), 1)
            self.assertTrue(
                any("semantic_overlap_ratio=" in line for line in overlap_conflicts[0].evidence)
            )

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
        self.assertEqual(profile.requested_policy_pack, "auto")
        self.assertEqual(profile.policy_pack, "openai-gpt5")
        self.assertEqual(profile.policy_resolution, "inferred")

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

            self.assertEqual(profile.requested_policy_pack, "auto")
            self.assertEqual(profile.policy_pack, "claude-4x")
            self.assertEqual(profile.policy_resolution, "inferred")

    def test_profile_infers_gemini_policy_pack(self) -> None:
        profile = load_profile(
            None,
            root_path=str(ROOT),
            policy_pack="auto",
            agent_runtime="gemini-cli",
            model_family="gemini-2.5-pro",
        )

        self.assertEqual(profile.policy_pack, "gemini-25")
        self.assertEqual(profile.policy_resolution, "inferred")

    def test_profile_infers_qwen_policy_pack(self) -> None:
        profile = load_profile(
            None,
            root_path=str(ROOT),
            policy_pack="auto",
            agent_runtime="qwen-code",
            model_family="qwen3-coder",
        )

        self.assertEqual(profile.policy_pack, "qwen-3")
        self.assertEqual(profile.policy_resolution, "inferred")

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

    def test_profile_validation_rejects_unknown_policy_pack_override(self) -> None:
        with self.assertRaises(ValueError) as exc:
            load_profile(
                None,
                root_path=str(ROOT),
                policy_pack="OpenAI_GPT5",
            )

        self.assertIn("Unknown policy pack", str(exc.exception))

    def test_profile_defaults_to_llm_disabled(self) -> None:
        profile = default_profile(str(ROOT))
        self.assertEqual(profile.llm_provider, "none")
        self.assertEqual(profile.requested_policy_pack, "generic-agentic")
        self.assertEqual(profile.policy_resolution, "default")

    def test_profile_accepts_llm_override(self) -> None:
        profile = load_profile(None, root_path=str(ROOT), llm_provider="mock")
        self.assertEqual(profile.llm_provider, "mock")

    def test_cli_surfaces_missing_provider_wrapper_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as exc:
                main(
                    [
                        "audit",
                        str(ROOT / "fixtures"),
                        "--output-dir",
                        tmp,
                        "--format",
                        "json",
                        "--llm",
                        "codex",
                    ]
                )

            self.assertEqual(exc.exception.code, 1)

    def test_openai_policy_pack_adjusts_scoring_for_rigid_browsing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "browsing_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Browsing Skill\n\n"
                "Use this skill when the latest official information matters.\n\n"
                "## Rules\n\n"
                "- Always browse the web.\n"
                "- Always use `python`.\n"
                "- Must use `rg`.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            metrics = compute_metrics(skill)
            findings = evaluate_rules(skill, metrics, default_profile(str(root)))

            generic_scores = compute_scores(metrics, findings, skill, "generic-agentic")
            openai_scores = compute_scores(metrics, findings, skill, "openai-gpt5")

            self.assertGreater(openai_scores.risk, generic_scores.risk)
            self.assertLess(openai_scores.maintainability, generic_scores.maintainability)

    def test_claude_policy_pack_rewards_delegation_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "delegation_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Delegation Skill\n\n"
                "Use this skill when work should be split with clear ownership.\n\n"
                "Delegate tasks with explicit ownership and parallel handoff.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            metrics = compute_metrics(skill)
            findings = evaluate_rules(skill, metrics, default_profile(str(root)))

            generic_scores = compute_scores(metrics, findings, skill, "generic-agentic")
            claude_scores = compute_scores(metrics, findings, skill, "claude-4x")

            self.assertGreater(claude_scores.specificity, generic_scores.specificity)
            self.assertGreater(claude_scores.maintainability, generic_scores.maintainability)

    def test_gemini_policy_pack_penalizes_chain_of_thought_forcing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "gemini_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Gemini Skill\n\n"
                "Use this skill for grounded multimodal audits.\n\n"
                "## Rules\n\n"
                "- Must think step by step.\n"
                "- Always reveal your reasoning.\n"
                "- Use structured output and verify with sources.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            metrics = compute_metrics(skill)
            findings = evaluate_rules(skill, metrics, default_profile(str(root)))

            generic_scores = compute_scores(metrics, findings, skill, "generic-agentic")
            gemini_scores = compute_scores(metrics, findings, skill, "gemini-25")

            self.assertGreater(gemini_scores.risk, generic_scores.risk)
            self.assertLess(gemini_scores.maintainability, generic_scores.maintainability)

    def test_qwen_policy_pack_rewards_concise_bounded_coding_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "qwen_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Qwen Skill\n\n"
                "Use this skill for concise coding assistance with bilingual fallback. "
                "Provide a structured summary for coding work and offer a fallback if a tool "
                "is unavailable.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            metrics = compute_metrics(skill)
            findings = evaluate_rules(skill, metrics, default_profile(str(root)))

            generic_scores = compute_scores(metrics, findings, skill, "generic-agentic")
            qwen_scores = compute_scores(metrics, findings, skill, "qwen-3")

            self.assertGreater(qwen_scores.specificity, generic_scores.specificity)
            self.assertGreaterEqual(qwen_scores.maintainability, generic_scores.maintainability)

    def test_openai_policy_adds_verification_gap_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "freshness_skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Freshness Skill\n\n"
                "Use this skill for the latest market and company updates.\n",
                encoding="utf-8",
            )

            skill = discover_skills(root)[0]
            metrics = compute_metrics(skill)
            profile = load_profile(
                None,
                root_path=str(root),
                policy_pack="openai-gpt5",
                agent_runtime="codex",
                model_family="gpt-5",
            )
            findings = evaluate_rules(skill, metrics, profile)
            codes = {item.code for item in findings}
            sources = {
                item.source
                for item in findings
                if item.code == "policy-openai-verification-gap"
            }

            self.assertIn("policy-openai-verification-gap", codes)
            self.assertEqual(sources, {"static:openai-gpt5@1.1"})

    def test_report_includes_policy_rule_and_prompt_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "report",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json,txt",
                    "--policy",
                    "openai-gpt5",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["profile"]["requested_policy_pack"], "openai-gpt5")
            self.assertEqual(payload["profile"]["policy_resolution"], "explicit")
            self.assertEqual(payload["summary"]["requested_policy_pack"], "openai-gpt5")
            self.assertEqual(payload["summary"]["policy_resolution"], "explicit")
            self.assertEqual(payload["summary"]["rules_version"], "openai-gpt5@1.1")
            self.assertEqual(payload["summary"]["prompt_version"], "openai-gpt5@1.1")
            summary_text = (Path(tmp) / "summary.txt").read_text(encoding="utf-8")
            self.assertIn("requested_policy_pack=openai-gpt5", summary_text)
            self.assertIn("policy_resolution=explicit", summary_text)
            self.assertIn("rules_version=openai-gpt5@1.1", summary_text)

    def test_report_marks_inferred_policy_resolution_when_auto_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "report",
                    str(ROOT / "fixtures"),
                    "--output-dir",
                    tmp,
                    "--format",
                    "json",
                    "--policy",
                    "auto",
                    "--agent-runtime",
                    "codex",
                    "--model-family",
                    "gpt-5",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["profile"]["requested_policy_pack"], "auto")
            self.assertEqual(payload["profile"]["policy_pack"], "openai-gpt5")
            self.assertEqual(payload["profile"]["policy_resolution"], "inferred")
            self.assertEqual(payload["summary"]["requested_policy_pack"], "auto")
            self.assertEqual(payload["summary"]["policy_resolution"], "inferred")

    def test_report_includes_rewrite_suggestions_per_skill(self) -> None:
        report = audit_path(ROOT / "fixtures", default_profile(str(ROOT / "fixtures"))).to_dict()

        skill = next(item for item in report["skills"] if item["skill"]["name"] == "conflicting_skill")
        rewrite = skill["rewrite"]

        self.assertEqual(rewrite["headline"], "Suggested rewrite")
        self.assertTrue(rewrite["rewritten_description"].startswith("Use this skill when"))
        self.assertGreaterEqual(len(rewrite["cleanup_actions"]), 1)
        self.assertTrue(
            any(
                action
                in {
                    "Fix or remove file references that no longer resolve.",
                    "Relax mandatory sequencing unless the tool or order is truly required.",
                    "Replace generic wording with a concrete trigger, scope, and expected outcome.",
                }
                for action in rewrite["cleanup_actions"]
            )
        )

    def test_diff_between_live_paths_reports_improvement_and_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = root / "before"
            after = root / "after"
            for folder in (before, after):
                folder.mkdir()
                (folder / "steady_skill").mkdir()
                (folder / "steady_skill" / "SKILL.md").write_text(
                    "# Steady Skill\n\nUse this skill for audits.\n",
                    encoding="utf-8",
                )

            (before / "weak_skill").mkdir()
            (before / "weak_skill" / "SKILL.md").write_text(
                "# Weak Skill\n\n"
                "This is a very general skill for many things.\n\n"
                "## Rules\n\n"
                "- Always use bash.\n"
                "- Always use python.\n",
                encoding="utf-8",
            )
            (after / "weak_skill").mkdir()
            (after / "weak_skill" / "SKILL.md").write_text(
                "# Weak Skill\n\n"
                "Use this skill for repository audits on Linux projects.\n\n"
                "## Rules\n\n"
                "- Use `rg` for search when available.\n",
                encoding="utf-8",
            )
            (after / "new_skill").mkdir()
            (after / "new_skill" / "SKILL.md").write_text(
                "# New Skill\n\nUse this skill for release summaries.\n",
                encoding="utf-8",
            )

            diff = build_diff(before, after, default_profile(str(root)))

            self.assertEqual(diff["summary"]["added_skills"], 1)
            self.assertEqual(diff["summary"]["removed_skills"], 0)
            statuses = {item["name"]: item["status"] for item in diff["skills"]}
            self.assertEqual(statuses["new_skill"], "added")
            self.assertEqual(statuses["weak_skill"], "improved")

    def test_diff_cli_can_compare_report_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before_skill = root / "before" / "example_skill"
            after_skill = root / "after" / "example_skill"
            before_skill.mkdir(parents=True)
            after_skill.mkdir(parents=True)
            (before_skill / "SKILL.md").write_text(
                "# Example Skill\n\n"
                "This is a very general skill for many things.\n",
                encoding="utf-8",
            )
            (after_skill / "SKILL.md").write_text(
                "# Example Skill\n\nUse this skill for repository cleanup.\n",
                encoding="utf-8",
            )

            before_out = root / "before_out"
            after_out = root / "after_out"
            diff_out = root / "diff_out"

            self.assertEqual(
                main(
                    [
                        "report",
                        str(before_skill),
                        "--output-dir",
                        str(before_out),
                        "--format",
                        "json",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "report",
                        str(after_skill),
                        "--output-dir",
                        str(after_out),
                        "--format",
                        "json",
                    ]
                ),
                0,
            )

            code = main(
                [
                    "diff",
                    str(before_out / "report.json"),
                    str(after_out / "report.json"),
                    "--output-dir",
                    str(diff_out),
                    "--format",
                    "json,md,txt",
                ]
            )

            self.assertEqual(code, 0)
            payload = json.loads((diff_out / "diff.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["changed_skills"], 1)
            self.assertTrue((diff_out / "diff.md").exists())
            summary_text = (diff_out / "diff.txt").read_text(encoding="utf-8")
            self.assertIn("changed_skills=1", summary_text)

    def test_rules_flag_non_canonical_skill_and_auxiliary_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Bad Skill"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "# Bad Skill\n\n"
                "Use this skill for audits.\n",
                encoding="utf-8",
            )
            (root / "My Helper.py").write_text("print('ok')\n", encoding="utf-8")

            skill = discover_skills(root)[0]
            findings = evaluate_rules(skill, compute_metrics(skill), default_profile(str(root)))
            codes = {item.code for item in findings}

            self.assertIn("non-canonical-skill-name", codes)
            self.assertIn("non-canonical-auxiliary-name", codes)


if __name__ == "__main__":
    unittest.main()
