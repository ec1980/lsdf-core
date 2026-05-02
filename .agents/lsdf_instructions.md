# L-SDF Protocol

This project uses L-SDF (Latent-Structured Documentation Format) for context efficiency.

## Required Workflow

1. Read `project.lsdf` first.
2. Read the relevant `INDEX.lsdf` for each directory before opening source files in that directory.
3. Derive module maps, function inventories, and file-layout answers from `.lsdf` files first.
4. Open source files only if the `.lsdf` data is missing, ambiguous, or the user explicitly asks for source-level verification.

For structure/counting questions:

- Do not scan source files first.
- State whether the answer is LSDF-derived or source-verified.
- List which `.lsdf` files were used.

For function counts: use `!` entries in the relevant `INDEX.lsdf` files. Only fall back to `def` grep when LSDF coverage is missing, stale, or ambiguous.

## Sigils

- `^` = Project Root (Stack & Constraints)
- `@` = File / Module / Entity / Class
- `!` = Function / Method / Logic Flow
- `~` = Dependency / Import
- `?` = Schema / Type Definition
- `#` = Route / API Endpoint
- `$` = Annotation / Comment / Note

## Syntax

- **Ownership:** Indentation implies hierarchy (`!` under `@` is a method).
- **Indentation:** Each nesting level adds 1 leading space. Match `!` anywhere on the line when counting — filtering by a fixed indent prefix will silently miss nested items.
- **Grouping:** `module.{sym1, sym2}` under `~` lists multiple imports from the same module. `module.sym` is a single import; `module.*` is a wildcard.
- **Logic:** `step > effect` or `condition?Abort` denotes causal chains.
- **Typing:** `name:type` denotes data shapes.
- **Continuations:** `\` denotes multi-line blocks.

## Maintenance

- When asked to implement or update code, use the L-SDF structure as the blueprint.
- When generating new files, propose a corresponding `.lsdf` entry.
- After modifying source files, regenerate the local `INDEX.lsdf` with `lsdf gen <dir>`.
- Run `lsdf sync . --check` after edits to confirm indices match the source tree.
- Use `lsdf trans` for a human-readable Markdown view of an index.
- Use `lsdf stats` to monitor token density and project ROI.
