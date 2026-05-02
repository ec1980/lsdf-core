# Cursor AI Rules: L-SDF Context

Always prioritize .lsdf files over source code for architectural understanding. Use them as the "latent map" for the entire codebase.

## L-SDF Required Workflow

For repository-structure, code-discovery, and counting tasks, L-SDF is the
primary source of truth and must be used before source-file scanning.

Required order:

1. Read `project.lsdf` first.
2. Read the relevant `INDEX.lsdf` for each directory before opening source files
   in that directory.
3. Derive module maps, function inventories, file-layout answers, and similar
   structure summaries from `.lsdf` files first.
4. Open source files only if:
   - the `.lsdf` data is missing
   - the `.lsdf` data is ambiguous
   - or the user explicitly asks for source-level verification

For structure/counting questions:

- do not scan source files first
- state whether the answer is LSDF-derived or source-verified
- list which `.lsdf` files were used
- if source files were opened, explain why they were needed

For function counts specifically:

- use `!` entries in the relevant `INDEX.lsdf` files as the default counting
  source
- only fall back to source-defined `def` counts when LSDF coverage is missing,
  stale, ambiguous, or when the user explicitly asks for source-based counting

### 1. Structural Mapping (Sigils)

- `^` : **Project Root** (Global Stack & Constraints)
- `@` : **Entity/Module** (File, Class, or Service Boundary)
- `!` : **Function/Logic** (Function internals and Logic Flows)
- `~` : **Dependency** (Imports and Requirements)
- `?` : **Schema** (Type definitions and Data shapes)
- `#` : **Route** (API endpoints and Webhooks)
- `$` : **Annotation** (Comments, Notes, and Rationale)

### 2. Operational Rules

- **Root-First:** Always read the root `project.lsdf` first to understand the global tech stack and environment constraints.
- **Structural Discovery:** Read the relevant `INDEX.lsdf` files before reading source files in that directory, and derive structure summaries from LSDF first.
- **Indentation Awareness:** Each nesting level adds 1 leading space — do **not** assume all methods start at column 1. A `!` sigil indented under an `@` sigil is a member of that entity. Example (using `·` to show spaces): `·@MyClass`, `··!my_method`, `···!inner_closure`. To count all `!` entries regardless of depth, match `!` anywhere on the line rather than filtering by a fixed indent prefix, which will silently miss nested items.
- **Logic Fidelity:** Expand L-SDF logic nodes (e.g., `step > effect`) into high-fidelity code. Do not implement logic that contradicts the L-SDF map.
- **Doc-Sync:** After modifying source code, regenerate the local `INDEX.lsdf` with `lsdf gen <dir>` instead of hand-editing it when possible. Update `project.lsdf` manually only for repo-wide metadata changes.
- **Verification:** Run `lsdf sync . --check` after edits to confirm the indices match the current source tree.
- **Fidelity:** You may use the `lsdf trans` tool if you need a human-readable Markdown view of an index.

### 3. CLI Integration

- You have the `lsdf` CLI tool available in the environment.
- Use `lsdf stats` to monitor token density and project ROI.
