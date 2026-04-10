from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit import audit_path
from core.conflict_report import build_report
from core.profile import load_profile
from core.reporting import render_markdown, render_summary
from core.schema_validation import validate_report_payload


def add_threshold_arguments(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--fail-on-threshold",
        type=float,
        default=None,
        help="Exit with code 2 when any risk score is greater than or equal to this threshold.",
    )
    subparser.add_argument(
        "--fail-on-conflict-priority",
        type=int,
        default=None,
        help=(
            "Exit with code 3 when any conflict priority is greater than or equal "
            "to this threshold."
        ),
    )


def add_shared_report_arguments(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("path", help="Path to a skill or directory.")
    subparser.add_argument("--profile", help="Path to profile JSON.", default=None)
    subparser.add_argument(
        "--format",
        dest="formats",
        default="json,md,txt",
        help="Comma-separated output formats: json,md,txt",
    )
    subparser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where report files will be written.",
    )
    subparser.add_argument(
        "--policy",
        dest="policy_pack",
        default=None,
        help="Override the policy pack. Use 'auto' to infer it from runtime/model family.",
    )
    subparser.add_argument(
        "--agent-runtime",
        default=None,
        help="Override the agent runtime in the evaluation profile.",
    )
    subparser.add_argument(
        "--model-family",
        default=None,
        help="Override the model family in the evaluation profile.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-auditor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit one skill or a directory of skills.")
    add_shared_report_arguments(audit_parser)
    add_threshold_arguments(audit_parser)

    conflicts_parser = subparsers.add_parser(
        "conflicts", help="Compare skills in a directory and report conflicts."
    )
    add_shared_report_arguments(conflicts_parser)
    add_threshold_arguments(conflicts_parser)
    conflicts_parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated skill names to compare explicitly.",
    )
    conflicts_parser.add_argument(
        "--folders",
        default=None,
        help="Comma-separated folder or group selectors relative to the target path.",
    )

    report_parser = subparsers.add_parser("report", help="Generate a full report for humans or CI.")
    add_shared_report_arguments(report_parser)
    add_threshold_arguments(report_parser)
    report_parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated skill names to include explicitly.",
    )
    report_parser.add_argument(
        "--folders",
        default=None,
        help="Comma-separated folder or group selectors relative to the target path.",
    )
    report_parser.add_argument(
        "--no-conflicts",
        action="store_true",
        help="Skip cross-skill conflict detection in the generated report.",
    )
    return parser


def write_outputs(report: dict, output_dir: Path, formats: list[str]) -> None:
    validate_report_payload(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    if "json" in formats:
        (output_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
    if "md" in formats:
        (output_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    if "txt" in formats:
        (output_dir / "summary.txt").write_text(render_summary(report), encoding="utf-8")


def determine_exit_code(
    report: dict, risk_threshold: float | None, conflict_threshold: int | None
) -> int:
    if risk_threshold is not None:
        if any(skill["scores"]["risk"] >= risk_threshold for skill in report["skills"]):
            return 2

    if conflict_threshold is not None:
        if any(
            conflict.get("priority", 0) >= conflict_threshold
            for conflict in report.get("conflicts", [])
        ):
            return 3

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    profile = load_profile(
        args.profile,
        root_path=args.path,
        policy_pack=getattr(args, "policy_pack", None),
        agent_runtime=getattr(args, "agent_runtime", None),
        model_family=getattr(args, "model_family", None),
    )
    if args.command == "audit":
        report = audit_path(Path(args.path), profile).to_dict()
    elif args.command in {"conflicts", "report"}:
        selected_skills = None
        if args.skills:
            selected_skills = {item.strip() for item in args.skills.split(",") if item.strip()}
        selected_folders = None
        if getattr(args, "folders", None):
            selected_folders = {item.strip() for item in args.folders.split(",") if item.strip()}
        report = build_report(
            Path(args.path),
            profile,
            include_conflicts=args.command == "conflicts" or not args.no_conflicts,
            selected_skills=selected_skills,
            selected_folders=selected_folders,
        ).to_dict()
    else:
        parser.error(f"Unsupported command: {args.command}")

    formats = [item.strip() for item in args.formats.split(",") if item.strip()]
    write_outputs(report, Path(args.output_dir), formats)

    return determine_exit_code(
        report,
        getattr(args, "fail_on_threshold", None),
        getattr(args, "fail_on_conflict_priority", None),
    )


if __name__ == "__main__":
    raise SystemExit(main())
