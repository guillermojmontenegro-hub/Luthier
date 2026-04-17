# Luthier

`Luthier` is the initial MVP of `skill-auditor`: a tool for auditing agent skills with static analysis, runtime-decoupled contracts, and outputs that are useful for both humans and CI pipelines.

Just like a newly purchased instrument still needs to be taken to a luthier so the fine details can be adjusted and the instrument can truly sound its best, agent skills also need tuning before they can perform reliably. `Luthier` is a skill tuner designed to help refine, inspect, and improve skills across ecosystems such as Codex, OpenCode, and Claude Code. Its goal is to make skill quality easier to measure, compare, and maintain before those instructions turn into runtime problems.

## Status

Today, the project can already:

- Discover skills from folders or individual files.
- Read `SKILL.md` and `AGENTS.md`, even when both live in the same folder.
- Compute objective metrics for description quality, size, constraints, examples, and context cost.
- Detect static findings related to quality, portability, and maintainability.
- Detect conflicts between skills and rank them with `priority` and `recommendation`.
- Generate `report.json`, `report.md`, and `summary.txt`.
- Validate normalized `profile` payloads and generated `report.json` against the versioned local schemas.
- Build structured prompts for skill audit, skill comparison, and report synthesis.
- Run a mock LLM adapter end-to-end for tests and integration scaffolding.
- Enable optional mock-backed LLM findings from the CLI without changing the static-first default path.

LLM-based analysis is still optional. The repository now includes the
`LLMAdapter` contract, structured prompt builders, and a `MockLLMAdapter`
intended for tests and integration scaffolding, while the core audit path still
works entirely without any external provider.
When enabled, the mock adapter can enrich per-skill findings, compare skill
pairs, and generate a final synthesis summary in the report output.

## Structure

```text
cli/         Command-line entrypoint
core/        Discovery, parsing, metrics, rules, scoring, and reports
adapters/    Contracts for optional LLM integrations
policies/    Policy packs and signals by model family
prompts/     Versioned structured prompts for optional LLM adapters
schemas/     Input and output JSON schemas
docs/        Architecture, profile, scoring, and output docs
fixtures/    Example skills for tests
tests/       Test suite
```

Naming conventions used by the project today:

- Python modules and helper files: lowercase `snake_case`.
- Skill directory names: lowercase `snake_case`.
- Policy pack identifiers: lowercase `kebab-case`.
- Generated reports: `report.json`, `report.md`, and `summary.txt`.

Reference docs:

- [architecture.md](/mnt/ssd_storage/ParaAgentes/Luthier/docs/architecture.md)
- [evaluation-profile.md](/mnt/ssd_storage/ParaAgentes/Luthier/docs/evaluation-profile.md)
- [output-and-scoring.md](/mnt/ssd_storage/ParaAgentes/Luthier/docs/output-and-scoring.md)

## Requirements

- `Python 3.11+`

## Installation

Editable mode:

```bash
python3 -m pip install -e .
```

Without installing the package, it can also be run with:

```bash
python3 -m cli.main --help
```

## Quick Start

Audit a folder:

```bash
python3 -m cli.main audit fixtures --output-dir out
```

Audit a single skill:

```bash
python3 -m cli.main audit fixtures/simple_skill --output-dir out
```

Compare conflicts between skills:

```bash
python3 -m cli.main conflicts fixtures --output-dir out
```

Compare an explicit subset:

```bash
python3 -m cli.main conflicts fixtures \
  --skills simple_skill,conflicting_skill \
  --output-dir out
```

Compare only skills inside selected folders or groups:

```bash
python3 -m cli.main conflicts fixtures \
  --folders unix,windows \
  --output-dir out
```

Generate a full report with explicit profile overrides:

```bash
python3 -m cli.main report fixtures \
  --model-family gpt-5 \
  --agent-runtime codex \
  --policy auto \
  --format json,md \
  --output-dir out
```

Fail in CI if any skill exceeds a risk threshold:

```bash
python3 -m cli.main audit fixtures \
  --fail-on-threshold 7 \
  --output-dir out
```

Fail in CI if the combined report contains high-priority conflicts:

```bash
python3 -m cli.main report fixtures \
  --fail-on-threshold 7 \
  --fail-on-conflict-priority 250 \
  --output-dir out
```

Run the static pipeline plus mock LLM scaffolding:

```bash
python3 -m cli.main audit fixtures \
  --llm mock \
  --output-dir out
```

## Main Flags

### `audit`

- `path`: file or folder to audit.
- `--profile`: optional JSON profile.
- `--format`: comma-separated output formats. Supports `json`, `md`, `txt`.
- `--output-dir`: destination folder.
- `--policy`: override the policy pack, or use `auto` to infer it.
- `--agent-runtime`: override the runtime in the evaluation profile.
- `--model-family`: override the model family in the evaluation profile.
- `--llm`: optional LLM provider. Supports `off`, `mock`, `codex`, `claude-code`, and `opencode`.
- `--fail-on-threshold`: returns exit code `2` if any risk score exceeds the threshold.
- `--fail-on-conflict-priority`: returns exit code `3` if any conflict priority exceeds the threshold.

### `conflicts`

- `path`: folder containing the skills to compare.
- `--profile`: optional JSON profile.
- `--format`: comma-separated output formats.
- `--output-dir`: destination folder.
- `--policy`: override the policy pack, or use `auto` to infer it.
- `--agent-runtime`: override the runtime in the evaluation profile.
- `--model-family`: override the model family in the evaluation profile.
- `--llm`: optional LLM provider. Supports `off`, `mock`, `codex`, `claude-code`, and `opencode`.
- `--skills`: comma-separated list to compare an explicit subset.
- `--folders`: comma-separated list of folders or groups relative to the target path.
- `--fail-on-threshold`: returns exit code `2` if any included skill exceeds the risk threshold.
- `--fail-on-conflict-priority`: returns exit code `3` if any conflict exceeds the priority threshold.

### `report`

- `path`: skill or folder to report on.
- `--profile`: optional JSON profile.
- `--format`: comma-separated output formats.
- `--output-dir`: destination folder.
- `--policy`: override the policy pack, or use `auto` to infer it.
- `--agent-runtime`: override the runtime in the evaluation profile.
- `--model-family`: override the model family in the evaluation profile.
- `--llm`: optional LLM provider. Supports `off`, `mock`, `codex`, `claude-code`, and `opencode`.
- `--skills`: comma-separated list to include an explicit subset.
- `--folders`: comma-separated list of folders or groups relative to the target path.
- `--no-conflicts`: skip conflict detection and emit only per-skill analysis.
- `--fail-on-threshold`: returns exit code `2` if any included skill exceeds the risk threshold.
- `--fail-on-conflict-priority`: returns exit code `3` if any conflict exceeds the priority threshold.

## Evaluation Profile

The auditor accepts a JSON profile to contextualize the analysis. A base example is available at [profile.example.json](/mnt/ssd_storage/ParaAgentes/Luthier/profile.example.json).

Current fields:

- `language`
- `shell`
- `operating_system`
- `network_access`
- `approval_mode`
- `requested_policy_pack`
- `policy_pack`
- `policy_resolution`
- `agent_runtime`
- `model_family`
- `llm_provider`
  Supports `none`, `mock`, `codex`, `claude-code`, and `opencode`.

If `--profile` is not provided, a default local profile is used.

Today the policy pack can also be inferred automatically:

- `openai-gpt5` for `gpt`/`openai` model families or Codex-like runtimes.
- `claude-4x` for Claude-oriented model families or runtimes.
- `generic-agentic` as the fallback.

## Outputs

Each run can generate:

- `report.json`: stable structured output for automation.
- `report.md`: human-readable report for review.
- `summary.txt`: short summary, friendly for CI and scripts.

The report summary also records the active `policy pack`, `rules_version`, and
`prompt_version` so runs remain traceable as runtime-specific heuristics evolve.
It now also records `requested_policy_pack` and `policy_resolution`, so it is
clear whether the selected pack came from an explicit override, inference, or
the default profile.
When conflict detection runs on larger collections, the summary also records
how many similarity clusters were built plus how many skill pairs were compared
or skipped by the clustering prefilter.

In `conflicts` mode, each conflict includes:

- `severity`
- `category`
- `evidence`
- `priority`
- `recommendation`
- `cluster_id`
- `cluster_size`
- `comparison_context`

## What It Analyzes Today

Examples of individual findings already implemented:

- Descriptions that are too long or too vague.
- References to missing files.
- Platform-specific instructions when the profile does not match.
- Unnecessary language mixing.
- Excessive constraints.
- Over-specified flows.
- Rigid tool or sequence forcing.
- Internal duplication of instructions.
- Imbalance between length and operational value.

Examples of conflicts between skills:

- Incompatible shell or OS assumptions.
- Opposing policies on follow-up questions.
- Opposing policies on web browsing.
- Required vs forbidden tools.
- Textual or structural overlap.
- `misleading-discovery` cases where two skills overlap and their descriptions may lead to the wrong selection.

## Tests

Run the suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run lint locally:

```bash
python3 -m pip install -e .[dev]
python3 -m ruff check .
```

The repository also includes a GitHub Actions workflow at [.github/workflows/ci.yml](/mnt/ssd_storage/ParaAgentes/Luthier/.github/workflows/ci.yml) that runs lint, tests, generates a report, and uploads the resulting artifacts.

## LLM Scaffolding

The current optional LLM path includes:

- [adapters/llm.py](/mnt/ssd_storage/ParaAgentes/Luthier/adapters/llm.py)
  for the prompt and result contracts.
- [adapters/mock.py](/mnt/ssd_storage/ParaAgentes/Luthier/adapters/mock.py)
  for a deterministic end-to-end mock adapter.
- [prompts/structured.py](/mnt/ssd_storage/ParaAgentes/Luthier/prompts/structured.py)
  for versioned prompt builders.

Minimal command-backed adapters are now included for `codex`,
`claude-code`, and `opencode`, in addition to the deterministic `mock`
adapter. The command-backed adapters expect a wrapper command that reads the
structured prompt JSON from stdin and prints a structured JSON response to
stdout. You can override the command with `LUTHIER_CODEX_CMD`,
`LUTHIER_CLAUDE_CODE_CMD`, or `LUTHIER_OPENCODE_CMD`.

## Short Roadmap

The most natural next steps for the MVP are:

1. Expand policy packs.
2. Add provider-backed LLM adapters beyond the mock implementation.
3. Reduce noise for larger collections with clustering or richer similarity.
4. Add diff support between skill versions or snapshots.
5. Tighten policy-specific scoring heuristics.

## Development

The detailed implementation status is available in [PLAN.md](/mnt/ssd_storage/ParaAgentes/Luthier/PLAN.md).
