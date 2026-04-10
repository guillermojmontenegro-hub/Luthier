from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from core.models import DiscoveredSkill, FileReference
from core.parser import (
    extract_description,
    extract_examples,
    extract_file_references,
    extract_restriction_lines,
    extract_sections,
    extract_usage_lines,
)


SKILL_FILENAMES = ("SKILL.md", "AGENTS.md")
SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".ts"}


def _is_script(path: Path) -> bool:
    return path.suffix.lower() in SCRIPT_SUFFIXES or path.stat().st_mode & 0o111


def _detect_platform_signals(content: str, auxiliary_files: list[Path]) -> list[str]:
    lowered = content.lower()
    signals: set[str] = set()
    for token in ("bash", "zsh", "powershell", "cmd.exe", "linux", "macos", "windows", "python", "node"):
        if token in lowered:
            signals.add(token)
    for item in auxiliary_files:
        if item.suffix.lower() in {".ps1", ".bat"}:
            signals.add("windows")
        if item.suffix.lower() in {".sh", ".bash", ".zsh"}:
            signals.add("unix-shell")
    return sorted(signals)


def _detect_language_mix(content: str) -> dict[str, int]:
    lowered = content.lower()
    english_markers = ("the ", "must ", "always ", "never ", "should ")
    spanish_markers = (" el ", " la ", " debe ", " siempre ", " nunca ", " usar ")
    english_hits = sum(lowered.count(token) for token in english_markers)
    spanish_hits = sum(lowered.count(token) for token in spanish_markers)
    return {"en": english_hits, "es": spanish_hits}


def _resolve_reference(base_dir: Path, reference: str) -> FileReference:
    clean_ref = reference.split("#", 1)[0]
    candidate = (base_dir / clean_ref).resolve()
    try:
        exists = candidate.exists()
    except OSError:
        exists = False
    return FileReference(path=clean_ref, exists=exists)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combine_contents(files: list[Path]) -> str:
    chunks: list[str] = []
    for item in files:
        chunks.append(_read_text(item).strip())
    return "\n\n".join(chunk for chunk in chunks if chunk)


def _skill_total_size_bytes(main_files: list[Path], auxiliary_files: list[Path]) -> int:
    total = 0
    for item in [*main_files, *auxiliary_files]:
        try:
            total += item.stat().st_size
        except OSError:
            continue
    return total


def discover_skills(root_path: Path) -> list[DiscoveredSkill]:
    path = root_path.resolve()
    if path.is_file():
        candidates = [path]
    else:
        candidates = sorted(candidate for name in SKILL_FILENAMES for candidate in path.rglob(name))

    discovered: list[DiscoveredSkill] = []

    grouped: dict[Path, list[Path]] = defaultdict(list)
    for candidate in candidates:
        if candidate.name in SKILL_FILENAMES:
            grouped[candidate.parent].append(candidate)

    for base_dir, main_files in sorted(grouped.items(), key=lambda item: str(item[0])):
        ordered_main_files = sorted(main_files, key=lambda item: (item.name != "SKILL.md", item.name))
        primary_file = ordered_main_files[0]
        content = _combine_contents(ordered_main_files)
        auxiliary_files = sorted(
            item for item in base_dir.iterdir() if item.is_file() and item not in set(ordered_main_files)
        )
        scripts = [str(item.relative_to(base_dir)) for item in auxiliary_files if _is_script(item)]
        description = extract_description(content)
        name = base_dir.name
        references = [_resolve_reference(base_dir, ref) for ref in extract_file_references(content)]

        discovered.append(
            DiscoveredSkill(
                name=name,
                root_path=str(base_dir),
                main_file=str(primary_file),
                source_files=[str(item) for item in ordered_main_files],
                description=description,
                usage_lines=extract_usage_lines(content),
                restriction_lines=extract_restriction_lines(content),
                examples=extract_examples(content),
                auxiliary_files=[str(item.relative_to(base_dir)) for item in auxiliary_files],
                scripts=scripts,
                references=references,
                platform_signals=_detect_platform_signals(content, auxiliary_files),
                language_mix=_detect_language_mix(content),
                content=content,
                sections=extract_sections(content),
                total_size_bytes=_skill_total_size_bytes(ordered_main_files, auxiliary_files),
            )
        )

    return discovered
