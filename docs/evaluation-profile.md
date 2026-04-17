# Evaluation Profile

The evaluation profile tells the auditor which environment the skill is expected
to run in. This is how static findings become contextual instead of generic.

Example file: [profile.example.json](/mnt/ssd_storage/ParaAgentes/Luthier/profile.example.json)

## Purpose

The same skill can look valid or risky depending on the runtime assumptions.

Examples:

- A skill that insists on `PowerShell` is less portable when the profile says
  `operating_system=linux`.
- A policy pack aligned with `codex` and `gpt-5` may choose different defaults
  than one aligned with Claude runtimes.

## Fields

### Identity and scope

- `version`
  Version of the profile document.
- `name`
  Human-friendly profile name.
- `root_path`
  Base path used for the run.
- `output_formats`
  Expected output formats. Must be any subset of `json`, `md`, and `txt`.

### Environment assumptions

- `language`
  Dominant working language for instructions.
- `shell`
  Expected shell, for example `bash` or `powershell`.
- `operating_system`
  Expected OS family such as `linux` or `windows`.
- `network_access`
  Whether network access is available.
- `approval_mode`
  Approval model expected by the runtime.
- `runtime_agnostic`
  Whether the target behavior should stay generic across runtimes.

### Runtime targeting

- `policy_pack`
  Policy pack name. Can be explicit or inferred.
- `requested_policy_pack`
  The originally requested policy selection, including `auto` when inference
  was requested.
- `policy_resolution`
  How the final `policy_pack` was chosen: `default`, `explicit`, or
  `inferred`.
- `agent_runtime`
  Runtime family such as `generic`, `codex`, or `claude-code`.
- `model_family`
  Model family such as `generic`, `gpt-5`, or `claude-4.1`.
- `llm_provider`
  Optional LLM backend for enriched findings. Today supports `none`, `mock`,
  `codex`, `claude-code`, and `opencode`.

## Defaults

If no profile is provided, the CLI builds a default local profile with:

- `language=es`
- `shell=bash`
- `operating_system=linux`
- `network_access=enabled`
- `approval_mode=on-request`
- `runtime_agnostic=true`
- `policy_pack=generic-agentic`
- `requested_policy_pack=generic-agentic`
- `policy_resolution=default`
- `agent_runtime=generic`
- `model_family=generic`
- `llm_provider=none`

## Policy Pack Inference

When `--policy auto` is used, or when the profile omits a concrete pack, the
runtime is inferred as follows:

- `openai-gpt5`
  Chosen for `gpt` or `openai` model families, and for Codex-like runtimes.
- `claude-4x`
  Chosen for Claude-oriented model families or runtimes.
- `generic-agentic`
  Fallback when no stronger signal is present.

The resolved profile is emitted as part of the report so downstream automation
can distinguish between an explicit pack choice and an inferred one.

## Validation Rules

Profiles are validated after normalization, not only when loaded from disk.

That means:

- user-provided profile files are validated,
- default profiles are validated too,
- CLI overrides must still produce a schema-valid final profile.

If validation fails, the run stops before audit output is generated.
