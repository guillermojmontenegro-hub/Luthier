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

LLM-based analysis is still reserved for a later expansion. The foundation already includes the `LLMAdapter` contract, but the current flow works entirely without any external provider.

## Structure

```text
cli/         Command-line entrypoint
core/        Discovery, parsing, metrics, rules, scoring, and reports
adapters/    Contracts for optional LLM integrations
policies/    Policy packs and signals by model family
prompts/     Reserved place for versioned prompts
schemas/     Input and output JSON schemas
fixtures/    Example skills for tests
tests/       Test suite
```

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

Fail in CI if any skill exceeds a risk threshold:

```bash
python3 -m cli.main audit fixtures \
  --fail-on-threshold 7 \
  --output-dir out
```

## Main Flags

### `audit`

- `path`: file or folder to audit.
- `--profile`: optional JSON profile.
- `--format`: comma-separated output formats. Supports `json`, `md`, `txt`.
- `--output-dir`: destination folder.
- `--fail-on-threshold`: returns exit code `2` if any risk score exceeds the threshold.

### `conflicts`

- `path`: folder containing the skills to compare.
- `--profile`: optional JSON profile.
- `--format`: comma-separated output formats.
- `--output-dir`: destination folder.
- `--skills`: comma-separated list to compare an explicit subset.

## Evaluation Profile

The auditor accepts a JSON profile to contextualize the analysis. A base example is available at [profile.example.json](/mnt/ssd_storage/ParaAgentes/Luthier/profile.example.json).

Current fields:

- `language`
- `shell`
- `operating_system`
- `network_access`
- `approval_mode`
- `policy_pack`
- `agent_runtime`
- `model_family`

If `--profile` is not provided, a default local profile is used.

## Outputs

Each run can generate:

- `report.json`: stable structured output for automation.
- `report.md`: human-readable report for review.
- `summary.txt`: short summary, friendly for CI and scripts.

In `conflicts` mode, each conflict includes:

- `severity`
- `category`
- `evidence`
- `priority`
- `recommendation`

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

## Short Roadmap

The most natural next steps for the MVP are:

1. Add more filters and ranking to `conflicts` mode.
2. Introduce the `report` command.
3. Harden CI with schema validation, linting, and thresholds.
4. Expand policy packs.
5. Add a first end-to-end LLM adapter.

## Development

The detailed implementation status is available in [PLAN.md](/mnt/ssd_storage/ParaAgentes/Luthier/PLAN.md).
