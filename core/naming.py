from __future__ import annotations

import re
from pathlib import Path

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
MODULE_BASENAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
POLICY_PACK_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

CANONICAL_REPORT_FILENAMES = {
    "json": "report.json",
    "md": "report.md",
    "txt": "summary.txt",
}


def is_canonical_skill_name(name: str) -> bool:
    return bool(SKILL_NAME_PATTERN.fullmatch(name))


def is_canonical_module_basename(name: str) -> bool:
    return bool(MODULE_BASENAME_PATTERN.fullmatch(name))


def is_canonical_policy_pack_name(name: str) -> bool:
    return bool(POLICY_PACK_PATTERN.fullmatch(name))


def non_canonical_auxiliary_paths(paths: list[str]) -> list[str]:
    invalid: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not is_canonical_module_basename(path.stem):
            invalid.append(raw_path)
    return invalid
