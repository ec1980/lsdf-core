# Changelog

All notable changes to this project will be documented in this file.

## 1.1.7 - 2026-06-01

### Fixed

- `lsdf init --ci` now renders the generated GitHub Actions workflow with the currently installed `lsdf-core` version pinned in the install step, preventing CI from pulling a newer PyPI release and rewriting indices with different output.
- All file I/O in `gen`, `sync`, and `trans` now explicitly passes `encoding="utf-8"` to `open()`. On Windows the previous default (`cp1252`) silently mangled Unicode characters in docstrings (e.g. em dash `—`, multiplication sign `×`) written into `INDEX.lsdf` and `INDEX.detail.lsdf`.

## 1.1.6 - 2026-05-07

### Changed

- Added `lsdf clean` with support for removing generated index files by default and undoing `lsdf init` bootstrap files with `--all`, including managed LSDF blocks in agent config files.
- Improved `lsdf init` file reporting and bootstrap behavior: ensured `.lsdf/` is present in `.lsdfignore`, limited output to touched files, and avoided rewriting `project.lsdf` on same-version reruns.
- Updated agent-instruction messaging so append and upgrade flows explicitly reference `.lsdf/lsdf_instructions.md` as the source file.
- Refreshed `README.md` and `docs/CLI.md` to document `lsdf clean` and match the CLI help command order.

## 1.1.5 - 2026-05-05

### Changed

- `lsdf stats` report redesigned: simplified to assume prompt caching as baseline, new table layout with labeled columns, file counts, token counts, compression ratio, and color-coded cost comparison.
- `lsdf init` now prints individual "Created" or "Updated" lines per template file instead of a single count summary.
- `lsdf init` no longer prints "Rebuilding" for a fresh repo that already has L-SDF protocol in agent config files — shows "Initializing" instead.
- README refreshed: shorter intro, demo GIF, tightened ROI section, bold bullet labels in philosophy section.

## 1.1.4 - 2026-05-05

### Fixed

- `lsdf init` no longer prints a "Template source not found" warning when installed via pipx or pip (non-editable). Templates are now packaged inside `src/_templates/` so they are included in the wheel and accessible at runtime regardless of install mode.

## 1.1.3 - 2026-05-05

### Changed

- Tightened `lsdf gen` annotation extraction so leading comments and docstring first lines longer than 80 characters are omitted from `INDEX.detail.lsdf`.
- Kept annotation extraction deterministic and spec-aligned by preserving concise high-value comments and short class/function docstrings without adding generation flags.
- Refreshed the Hello World example and README to use a more typical small source file, updated the generated index examples, and clarified that module docstrings are not extracted into detail indices.

## 1.1.2 - 2026-05-04

### Changed

- Refined package metadata in `pyproject.toml`, including project URLs, Python version requirements, classifiers, and license metadata.
- Clarified README and spec language around agent-first usage, call edges, workflow guidance, and current limitations.
- Added release-supporting project docs including `SECURITY.md`.
- Fixed `lsdf init` to rebuild missing `project.lsdf` and refresh existing agent L-SDF instructions when prior L-SDF state is detected.
- Switched `lsdf init` instruction management to explicit `LSDF:START` / `LSDF:END` markers so updates do not remove unrelated text in agent config files.
- Fixed `lsdf init` to avoid copying `.lsdf` template files onto themselves when run inside the `lsdf-core` repository.

## 1.1.1 - 2026-05-04

### Changed

- `lsdf stats` now reports session cost and savings with configurable pricing, turns, cache hit rate, and drilldown rate.
- `lsdf trans` is now one-way: `.lsdf` to Markdown only.
- CLI docs and README were updated to match the current `stats` output and `trans` behavior.

## 1.1.0 - 2026-05-03

### Added

- Two-tier index generation with both `INDEX.lsdf` and `INDEX.detail.lsdf`.
- `INDEX.detail.lsdf` as a dedicated layer for signatures, schemas, call edges, and richer contract detail.
- Compact type syntax for detail indices, including `s`, `i`, `f`, `b`, `a`, `[x]`, `{k:v}`, `q[x]`, `l[...]`, and `x?`.
- Updated LSDF-first agent workflow that reads `project.lsdf`, then `INDEX.lsdf`, then `INDEX.detail.lsdf` when more detail is needed.
- `.lsdf/meta.json` support for tracking both navigation and detail index metadata.

### Changed

- L-SDF moved from a single-index directory model in 1.0 to a two-tier index model in 1.1.
- `lsdf gen` now generates both navigation and detail indices by default.
- Signatures, schemas, and call edges are now expected in `INDEX.detail.lsdf` instead of being mixed into a single index.
- Detail indices use compact type forms to improve density and agent readability.

### Upgrade Notes

- Re-run `lsdf gen` to generate both `INDEX.lsdf` and `INDEX.detail.lsdf`.
- Update agent instructions and workflows to reference the two-tier read order.
- Expect line counts and formatting to differ from 1.0 because detail data is now split into a separate index and encoded more compactly.
