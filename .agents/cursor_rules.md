## Cursor AI Rules: L-SDF Context

Always prioritize .lsdf files over source code for architectural understanding. Use them as the "latent map" for the entire codebase.

### 1. Structural Mapping (Sigils)

- `^` : **Project Root** (Global Stack & Constraints)
- `@` : **Entity/Module** (File, Class, or Service Boundary)
- `!` : **Function/Logic** (Function internals and Logic Flows)
- `~` : **Dependency** (Imports and Requirements)
- `?` : **Schema** (Type definitions and Data shapes)
- `#` : **Route** (API endpoints and Webhooks)
- `$` : **Annotation** (Comments, Notes, and Rationale)

> **Reference:** If you encounter ambiguous syntax, read `SPEC.md` in the repo root.
> **CLI Reference:** If you need exact `lsdf` command usage or options, read `docs/CLI.md`.

### 2. Operational Rules

- **Root-First:** Always read the root `project.lsdf` first to understand the global tech stack and environment constraints.
- **Structural Discovery:** When investigating features or bugs, use `@Codebase` to scan all `INDEX.lsdf` files before reading `.py` or `.ts` files.
- **Indentation Awareness:** Respect the 2-space hierarchy. A `!` sigil indented under an `@` sigil is a member of that entity.
- **Logic Fidelity:** Expand L-SDF logic nodes (e.g., `step > effect`) into high-fidelity code. Do not implement logic that contradicts the L-SDF map.
- **Doc-Sync:** After modifying source code, regenerate the local `INDEX.lsdf` with `lsdf gen <dir>` instead of hand-editing it when possible. Update `project.lsdf` manually only for repo-wide metadata changes.
- **Verification:** Run `lsdf sync . --check` after edits to confirm the indices match the current source tree.

### 3. CLI Integration

- You have the `lsdf` CLI tool available in the environment.
- Use `lsdf stats` to monitor token density and project ROI.
- Use `lsdf trans <file>` to generate a human-readable Markdown view of any L-SDF index for validation.
