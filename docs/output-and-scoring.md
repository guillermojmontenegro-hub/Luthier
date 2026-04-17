# Output And Scoring

This document describes the report payload, the generated files, the current
score formulas, and the practical limits of the static analyzer.

## Output Files

Each run can generate up to three files:

- `report.json`
  Canonical structured output for automation.
- `report.md`
  Human-readable audit summary.
- `summary.txt`
  Small CI-friendly summary.

Those filenames are part of the current convention and should remain stable for
scripts and CI integrations.

## `report.json` Shape

Top-level fields:

- `schema_version`
  Version of the report contract.
- `generated_at`
  UTC timestamp for the run.
- `profile`
  The normalized evaluation profile used for the run.
- `skills`
  Per-skill analysis entries.
- `conflicts`
  Cross-skill conflicts, or an empty list if not requested.
- `summary`
  Aggregate counters and top-line indicators.

### `skills[]`

Each entry contains:

- `skill`
  Normalized discovered skill metadata and extracted content signals.
- `metrics`
  Objective measurements produced by the analyzer.
- `findings`
  Static warnings or issues with `code`, `severity`, `message`, `evidence`, and
  `recommendation`.
- `scores`
  Derived scorecard values from `0.0` to `10.0`.

### `conflicts[]`

Each conflict contains:

- `left_skill`
- `right_skill`
- `severity`
- `category`
- `evidence`
- `priority`
- `recommendation`
- `cluster_id`
- `cluster_size`
- `comparison_context`

### `summary`

Current aggregate fields:

- `skill_count`
- `finding_count`
- `conflict_count`
- `average_risk`
- `highest_conflict_priority`
- `conflict_cluster_count`
- `conflict_pairs_compared`
- `conflict_pairs_skipped`
- `conflict_pairs_total`
- `llm_provider`
- `llm_finding_count`
- `llm_conflict_count`
- `llm_summary`
- `requested_policy_pack`
- `policy_resolution`
- `rules_version`
- `prompt_version`

## Score Definitions

All scores currently use a `0.0` to `10.0` range.

The analyzer now applies policy-pack-specific adjustments on top of the base
formula. This keeps the baseline deterministic while still reflecting
runtime-family priorities such as browsing discipline for GPT-style runtimes or
delegation clarity for Claude-style runtimes.

The active rule and prompt versions are also emitted in the report summary so
CI runs stay traceable when policy-specific heuristics evolve.
The summary also captures whether the policy pack was explicit, inferred, or
kept from the default profile.

### `risk`

`risk` is the weighted sum of findings, capped at `10.0`.

Severity weights today:

- `low = 0.8`
- `medium = 1.5`
- `high = 2.5`

This is the score most suitable for simple CI gating.

Policy adjustments may add small extra penalties when a policy pack marks a
skill as especially risky for that runtime family.

### `discoverability`

Starts at `10.0` and is reduced by:

- `2.0` if the description estimate exceeds `80` tokens.
- `3.0` if the description estimate is shorter than `6` tokens.
- up to `3.0` extra points from high non-operational ratio.

Interpretation:

- high score means the opening description is likely easier to select correctly,
- low score means the skill may be vague, bloated, or narratively noisy.

Policy packs may reward runtime-specific positive signals such as clearer
decision boundaries.

### `specificity`

Current formula:

`instruction_density * 220 + example_count * 0.8`

Then clamped into `0.0..10.0`.

Interpretation:

- high score means the skill contains concrete operating guidance,
- low score means it may be generic or underspecified.

Policy packs may reward concrete runtime-specific structure such as explicit
delegation boundaries.

### `portability`

Current formula:

`10.0 - min(6.0, tool_reference_count * 0.2)`

Interpretation:

- high score means the skill is less coupled to specific tools,
- low score means the skill references many tools and may travel poorly across
  runtimes.

### `maintainability`

Current formula:

`10.0 - min(6.0, restriction_count * 0.35 + section_count * 0.1)`

Interpretation:

- high score means the skill is easier to keep aligned and less rigid,
- low score means it has more structural and constraint overhead.

Policy packs may penalize runtime-specific anti-patterns such as rigid tool
forcing or blocking collaboration structure.

### `context_cost`

Directly derived from the metric `context_cost_score`, capped at `10.0`.

Interpretation:

- high score means the skill is expensive in context,
- low score means the skill is relatively cheap to load.

## Current Static Limitations

The static analyzer is intentionally conservative and deterministic.

Limits to keep in mind:

- It relies on heuristics, not semantic understanding.
- It estimates tokens rather than using provider-native tokenizers.
- It detects role or tone conflicts through textual signals, not through deep
  behavioral simulation.
- It can identify overlap and policy mismatches, but it does not yet judge
  nuanced instruction quality the way a strong model could.
- Clustering reduces pairwise noise in larger collections, but it still uses
  lightweight lexical, normalized intent, and structural signals rather than
  semantic embeddings.

## When LLM Analysis Is Worth Enabling

LLM analysis is not wired end-to-end yet, but the likely best use cases are
already clear.

Prefer static analysis only when:

- you need deterministic CI checks,
- cost and latency matter,
- the main risks are portability, duplication, broken references, or rigid
  constraints.

Prefer adding LLM analysis once adapters land when:

- skills overlap semantically but not lexically,
- you need rewrite suggestions instead of only findings,
- you want deeper reasoning about tone, ambiguity, and hidden behavioral drift,
- you are comparing larger skill sets where static overlap signals are not
  enough.

The intended model is static-first, LLM-second: the LLM should explain or refine
edge cases, not replace the cheap deterministic layer.
