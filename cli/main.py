from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit import audit_path
from core.conflict_report import build_report
from core.profile import load_profile
from core.reporting import render_markdown, render_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-auditor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit one skill or a directory of skills.")
    audit_parser.add_argument("path", help="Path to a skill or directory.")
    audit_parser.add_argument("--profile", help="Path to profile JSON.", default=None)
    audit_parser.add_argument(
        "--format",
        dest="formats",
        default="json,md,txt",
        help="Comma-separated output formats: json,md,txt",
    )
    audit_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where report files will be written.",
    )
    audit_parser.add_argument(
        "--fail-on-threshold",
        type=float,
        default=None,
        help="Exit with code 2 when any risk score is greater than or equal to this threshold.",
    )

    conflicts_parser = subparsers.add_parser("conflicts", help="Compare skills in a directory and report conflicts.")
    conflicts_parser.add_argument("path", help="Path to a directory of skills.")
    conflicts_parser.add_argument("--profile", help="Path to profile JSON.", default=None)
    conflicts_parser.add_argument(
        "--format",
        dest="formats",
        default="json,md,txt",
        help="Comma-separated output formats: json,md,txt",
    )
    conflicts_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where report files will be written.",
    )
    conflicts_parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated skill names to compare explicitly.",
    )
    return parser


def write_outputs(report: dict, output_dir: Path, formats: list[str]) -> None:
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    profile = load_profile(args.profile, root_path=args.path)
    if args.command == "audit":
        report = audit_path(Path(args.path), profile).to_dict()
    elif args.command == "conflicts":
        selected_skills = None
        if args.skills:
            selected_skills = {item.strip() for item in args.skills.split(",") if item.strip()}
        report = build_report(
            Path(args.path),
            profile,
            include_conflicts=True,
            selected_skills=selected_skills,
        ).to_dict()
    else:
        parser.error(f"Unsupported command: {args.command}")

    formats = [item.strip() for item in args.formats.split(",") if item.strip()]
    write_outputs(report, Path(args.output_dir), formats)

    threshold = getattr(args, "fail_on_threshold", None)
    if args.command == "audit" and threshold is not None:
        if any(skill["scores"]["risk"] >= threshold for skill in report["skills"]):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
