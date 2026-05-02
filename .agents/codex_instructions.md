## GitHub Copilot Instructions: L-SDF Blueprinting

This project uses L-SDF for token-optimized context. Use these files as your "source of truth" for architecture before generating code.

### 1. Blueprint Logic

- **Root Entry:** Always inspect the root `project.lsdf` for global tech stack and constraints.
- **Local Index:** Every directory contains an `INDEX.lsdf`. Use this to map the module's skeleton.
- **Logic Chains:** Use the `!` sigil lines as the step-by-step blueprint for function implementations.
- **Data Integrity:** Use `?` sigils to determine the correct types for variable assignments and interfaces.

### 2. Syntax Key

- `^` : Project Root / Global Env & Stack
- `@` : File / Module / Class / Object Boundary
- `!` : Function / Method / Internal Logic Chain
- `~` : Dependencies, Imports, and Requirements
- `?` : Schema, Interface Shapes, and Type Definitions
- `#` : API Routes / Endpoints / Webhooks
- `$` : Annotation / Comment / Note / Rationale

> **Reference:** If you encounter ambiguous syntax, read `SPEC.md` in the repo root.
> **CLI Reference:** If you need exact `lsdf` command usage or options, read `docs/CLI.md`.

### 3. Maintenance Policy

- **Proposed Docs:** When generating new files, always propose a corresponding `.lsdf` entry.
- **Indentation:** Children MUST be indented exactly 2 spaces under their parents.
- **Fidelity:** Logic chains (e.g., `Step A > Step B`) must be implemented as sequential operations in the source code.
- **Sync:** If you modify source files, regenerate the local `INDEX.lsdf` with `lsdf gen <dir>` instead of guessing the update by hand when possible. Update `project.lsdf` manually only when repo-wide metadata changes.
- **Verification:** Run `lsdf sync . --check` after edits to confirm the generated indices still match the source tree.
