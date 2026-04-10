from __future__ import annotations

import re


HEADER_RE = re.compile(r"^#{1,6}\s+(?P<title>.+)$", re.MULTILINE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
LIST_LINE_RE = re.compile(r"^\s*([-*]|\d+\.)\s+(?P<line>.+)$", re.MULTILINE)
REFERENCE_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|`([^`]+\.[A-Za-z0-9._-]+)`")
SECTION_RE = re.compile(r"^#{1,6}\s+(?P<title>.+)$", re.MULTILINE)
EXAMPLE_LINE_RE = re.compile(r"^\s*(?:example|ejemplo)\s*:?\s*(?P<line>.+)$", re.IGNORECASE | re.MULTILINE)

USAGE_SECTION_MARKERS = ("use", "usage", "when to use", "cuándo usar", "cuando usar")
RESTRICTION_SECTION_MARKERS = ("rule", "rules", "restriction", "restrictions", "constraint", "constraints")
EXAMPLE_SECTION_MARKERS = ("example", "examples", "ejemplo", "ejemplos")


def extract_sections(content: str) -> list[str]:
    return [match.group("title").strip() for match in HEADER_RE.finditer(content)]


def extract_description(content: str) -> str:
    lines: list[str] = []
    started = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if started:
                break
            started = True
            continue
        if not stripped and not lines:
            continue
        if stripped.startswith("```"):
            break
        if stripped.startswith(("-", "*")) or re.match(r"^\d+\.", stripped):
            break
        if stripped:
            lines.append(stripped)
    return " ".join(lines).strip()


def extract_section_bodies(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(content))
    for index, match in enumerate(matches):
        title = match.group("title").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections[title] = content[start:end].strip()
    return sections


def extract_file_references(content: str) -> list[str]:
    refs: list[str] = []
    for match in REFERENCE_RE.finditer(content):
        linked = match.group(2)
        code_ref = match.group(3)
        value = linked or code_ref
        if value and "/" not in value and "." not in value:
            continue
        if value:
            refs.append(value)
    return sorted(set(refs))


def strip_code_blocks(content: str) -> str:
    return CODE_BLOCK_RE.sub("", content)


def extract_list_lines(content: str) -> list[str]:
    return [match.group("line").strip() for match in LIST_LINE_RE.finditer(content)]


def _section_lines(content: str, markers: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for title, body in extract_section_bodies(content).items():
        normalized = title.lower().strip()
        if any(marker in normalized for marker in markers):
            lines.extend(extract_list_lines(body))
    return lines


def extract_usage_lines(content: str) -> list[str]:
    return _section_lines(content, USAGE_SECTION_MARKERS)


def extract_restriction_lines(content: str) -> list[str]:
    return _section_lines(content, RESTRICTION_SECTION_MARKERS)


def extract_examples(content: str) -> list[str]:
    examples = [match.group("line").strip() for match in EXAMPLE_LINE_RE.finditer(content)]
    for title, body in extract_section_bodies(content).items():
        normalized = title.lower().strip()
        if any(marker in normalized for marker in EXAMPLE_SECTION_MARKERS):
            for line in extract_list_lines(body):
                if line not in examples:
                    examples.append(line)
    return examples
