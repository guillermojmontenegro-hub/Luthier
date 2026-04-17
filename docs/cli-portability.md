# CLI Portability Evaluation

This note records whether `Luthier` should maintain a second CLI
implementation for portability reasons.

## Current Decision

Do not add a second CLI implementation yet.

The current Python CLI is sufficient for the project's present portability
needs because:

- the analyzer core is already runtime-decoupled and file-oriented,
- the tool contract is expressed through JSON schemas rather than Python-only
  internal types,
- the existing CLI surface is still small and stable,
- CI, report generation, and local execution already run through the same
  `python3 -m cli.main` entrypoint.

Adding a second CLI today would duplicate:

- argument parsing,
- profile normalization,
- output writing,
- exit-code behavior,
- compatibility testing across commands and formats.

That duplication would likely create more maintenance risk than portability
benefit at the current stage.

## Why Python Is Acceptable Today

- `Python 3.11+` is already the only hard runtime requirement.
- The generated artifacts are plain files: `report.json`, `report.md`,
  `summary.txt`, plus `diff.*`.
- The core logic is not tied to a Python-only runtime environment such as a web
  server, framework, or native extension boundary.
- The project already uses stable schemas and report contracts, so portability
  is preserved at the data boundary even with a single implementation.

## What Would Justify a Second CLI Later

A second implementation would become more reasonable if one or more of these
conditions become important:

1. A non-Python distribution target becomes mandatory, such as a Node-only
   plugin ecosystem or a single-binary environment where Python installation is
   unacceptable.
2. The project needs tighter embedding into another runtime that cannot invoke
   the Python process cleanly.
3. Startup latency, packaging constraints, or enterprise distribution
   requirements make the current Python packaging path a bottleneck.
4. The CLI surface stabilizes further and the schemas become the dominant
   interface, reducing the risk of behavior drift between implementations.

## Recommended Path If It Becomes Necessary

If a second CLI is ever added, it should be a thin wrapper over the same stable
contracts instead of a reimplementation of the analyzer logic.

Preferred sequence:

1. Keep the report and profile schemas as the primary public contract.
2. Keep conflict and diff behavior specified through fixture-based black-box
   tests.
3. Extract any remaining CLI-only decisions into contract-tested helper
   functions first.
4. Add the second CLI only after those cross-runtime expectations are pinned
   down in tests.

## Conclusion

Portability is acceptable today with a single Python CLI.
The project should invest in stable contracts and fixtures first, not in a
second command-line implementation.
