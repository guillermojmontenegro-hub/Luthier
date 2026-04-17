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

At this stage the project intentionally keeps a single Python CLI.
The portability evaluation lives in
[cli-portability.md](/mnt/ssd_storage/ParaAgentes/Luthier/docs/cli-portability.md)
and concludes that a second CLI implementation would add more duplication than
benefit for the current scope.

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
  Builds lightweight similarity clusters, limits deep pairwise comparisons in
  larger collections, and emits structured cross-skill conflicts with
  clustering traceability. The current similarity layer blends lexical overlap,
  normalized intent signatures, and structural signals.
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

When an `llm_provider` is enabled in the profile, the report builder can enrich
per-skill findings through the adapter boundary without replacing the static
analysis stages.

### `policies/`

Policy packs define runtime-family signals and provide the place where
model-specific heuristics can diverge without entangling the core analyzer.

Today they are used for profile normalization, pack selection, and bounded
score adjustments based on runtime-specific positive and negative signals.
They also define effective prompt and rule versions so policy evolution stays
traceable in generated reports.
Policy identifiers follow lowercase `kebab-case` so CLI overrides and report
metadata stay stable.

### `adapters/`

Adapters are reserved for optional LLM-based analysis.

The repository now includes:

- a deterministic mock adapter for tests,
- a reusable command-backed adapter base,
- minimal provider adapters for `codex`, `claude-code`, and `opencode`.

The static pipeline still works without any external provider.

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

## Naming Conventions

- Python modules under `cli/`, `core/`, `adapters/`, and `policies/` use
  lowercase `snake_case.py`.
- Skill folders are expected to use lowercase `snake_case`.
- Auxiliary skill files and scripts are expected to use lowercase
  `snake_case` basenames.
- Policy pack identifiers use lowercase `kebab-case`.
- Report outputs keep canonical filenames: `report.json`, `report.md`, and
  `summary.txt`.

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
