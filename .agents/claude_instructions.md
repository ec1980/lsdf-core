# AI Agent Instructions: L-SDF Protocol

This project uses L-SDF (Latent-Structured Documentation Format) for context efficiency.

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

### 1. SIGILS

- `^` = Project Root (Stack & Constraints)
- `@` = File / Module / Entity / Class
- `!` = Function / Method / Logic Flow
- `~` = Dependency / Import
- `?` = Schema / Type Definition
- `#` = Route / API Endpoint
- `$` = Annotation / Comment / Note

### 2. SYNTAX

- **Ownership:** Indentation implies hierarchy (e.g., `!` under `@` is a method).
- **Indentation:** Each nesting level adds 1 leading space. A top-level symbol has 1 space; a child of that symbol has 2 spaces; a grandchild has 3 spaces; and so on. The absolute column of a sigil indicates its depth — do **not** assume all methods start at column 1.
  - Example (using `·` to show spaces): `·@MyClass` (1 space = file-level class), `··!my_method` (2 spaces = method of that class), `···!inner` (3 spaces = closure inside that method).
  - **Counting rule:** To count all `!` entries regardless of depth, match `!` anywhere on the line (e.g., grep for `!` rather than `^ !`). Filtering by a fixed indent prefix will silently miss nested items.
- **Logic:** `step > effect` or `condition?Abort` denotes causal chains.
- **Typing:** `name:type` (e.g., `id:uuid`) denotes data shapes.
- **Continuations:** `\` denotes multi-line blocks (e.g., CLI arguments).

### 3. TASK PROTOCOL

- **Root-First:** Always read the root `project.lsdf` first to understand global tech stack and constraints.
- **Index-Discovery:** Read the local `INDEX.lsdf` in a directory before opening source files.
- **LSDF-First:** Derive structure summaries from `.lsdf` files before source scanning, and only open source files when the LSDF data is missing, ambiguous, or explicitly needs verification.
- **Expansion:** When asked to implement or update code, use the L-SDF logic as the blueprint.
- **Maintenance:** If you modify source code in a directory, regenerate that directory's `INDEX.lsdf` with `lsdf gen <dir>` rather than guessing the syntax by hand. If you change project-wide metadata, update `project.lsdf` manually.
- **Verification:** After code changes, run `lsdf sync . --check` to confirm the generated indices still match the source tree.
- **Fidelity:** You may use the `lsdf trans` tool if you need a human-readable Markdown view of an index.
