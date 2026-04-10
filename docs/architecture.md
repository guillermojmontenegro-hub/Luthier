# Architecture

`Luthier` is organized as a small layered pipeline. The intent is to keep the
core audit logic runtime-agnostic, while still allowing runtime-specific policy
packs and future LLM adapters to plug in without rewriting the analyzer.

## Layers

### `cli/`

The CLI is the orchestration boundary.

- Parses user intent and flags such as `--profile`, `--policy`,
  `--fail-on-threshold`, and `--fail-on-conflict-priority`.
- Loads and normalizes the evaluation profile.
- Triggers either per-skill audit mode or full cross-skill report mode.
- Validates report payloads before writing them.
- Returns CI-friendly exit codes.

### `core/`

The core contains the analysis pipeline and stable contracts.

- `discovery.py`
  Scans folders, finds `SKILL.md` and `AGENTS.md`, collects auxiliary files,
  scripts, platform signals, references, and normalized content blobs.
- `parser.py`
  Extracts descriptions, sections, usage lines, restriction lines, examples,
  and file references while tolerating imperfect markdown.
- `metrics.py`
  Computes objective measurements such as token estimates, examples, tool
  mentions, restriction count, and context cost.
- `rules.py`
  Converts metrics and raw signals into static findings.
- `conflicts.py`
  Compares skills pairwise and emits structured cross-skill conflicts.
- `scoring.py`
  Produces the scorecard from metrics and findings.
- `conflict_report.py`
  Builds the full in-memory report object, including filtering by skill or
  folder selectors.
- `reporting.py`
  Renders `report.md` and `summary.txt`.
- `schema_validation.py`
  Validates normalized profiles and report payloads against local versioned
  schemas.

### `policies/`

Policy packs define runtime-family signals and provide the place where
model-specific heuristics can diverge without entangling the core analyzer.

Today they are used mainly for profile normalization and pack selection.

### `adapters/`

Adapters are reserved for optional LLM-based analysis.

The current MVP only defines the contract boundary. The static pipeline works
without any external provider.

### `schemas/`

The schemas are the automation contract.

- `profile.schema.json` defines the normalized evaluation profile shape.
- `report.schema.json` defines the structured report shape that CI and external
  tooling can rely on.

## Flow

1. CLI reads flags and loads the profile.
2. Discovery finds and normalizes candidate skills.
3. Parsing extracts structured instruction blocks.
4. Metrics compute objective signals.
5. Rules produce per-skill findings.
6. Scoring derives the scorecard.
7. Conflict detection compares skills when requested.
8. Report assembly creates the canonical in-memory payload.
9. Schema validation checks the payload before any file is written.
10. Renderers emit `report.json`, `report.md`, and `summary.txt`.

## Design Principles

- Runtime-decoupled core
  Discovery, parsing, metrics, scoring, and reporting must remain useful even
  when no runtime-specific adapter is installed.
- Stable automation contract
  The JSON report is treated as a CI interface, not just a debug artifact.
- Static-first analysis
  The default path should be deterministic, cheap, and offline-friendly.
- Optional LLM expansion
  Future LLM analysis should enrich, not replace, the static pipeline.
