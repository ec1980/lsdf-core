# Changelog

All notable changes to this project will be documented in this file.

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
