## AI Agent Instructions: L-SDF Protocol

This project uses L-SDF (Latent-Structured Documentation Format) for context efficiency.

### 1. SIGILS

- `^` = Project Root (Stack & Constraints)
- `@` = File / Module / Entity / Class
- `!` = Function / Method / Logic Flow
- `~` = Dependency / Import
- `?` = Schema / Type Definition
- `#` = Route / API Endpoint
- `$` = Annotation / Comment / Note

> **Reference:** If you encounter ambiguous syntax, read `SPEC.md` in the repo root.
> **CLI Reference:** If you need exact `lsdf` command usage or options, read `docs/CLI.md`.

### 2. SYNTAX

- **Ownership:** Indentation implies hierarchy (e.g., `!` under `@` is a method).
- **Logic:** `step > effect` or `condition?Abort` denotes causal chains.
- **Typing:** `name:type` (e.g., `id:uuid`) denotes data shapes.
- **Continuations:** `\` denotes multi-line blocks (e.g., CLI arguments).

### 3. TASK PROTOCOL

- **Root-First:** Always read the root `project.lsdf` first to understand global tech stack and constraints.
- **Index-Discovery:** Read the local `INDEX.lsdf` in a directory before opening source files.
- **Expansion:** When asked to implement or update code, use the L-SDF logic as the blueprint.
- **Maintenance:** If you modify source code in a directory, regenerate that directory's `INDEX.lsdf` with `lsdf gen <dir>` rather than guessing the syntax by hand. If you change project-wide metadata, update `project.lsdf` manually.
- **Verification:** After code changes, run `lsdf sync . --check` to confirm the generated indices still match the source tree.
- **Fidelity:** You may use the `lsdf trans` tool if you need a human-readable Markdown view of an index.
