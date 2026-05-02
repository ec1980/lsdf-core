# L-SDF v1.0 Specification

## Core Sigils

| Sigil | Meaning | Purpose |
| :--- | :--- | :--- |
| `^` | **Root** | Project-level stack and global constraints. |
| `@` | **Entity** | File, class, module, or service boundary. |
| `!` | **Function** | Function, method, or logic flow. |
| `~` | **Dependency** | Imports and external requirements. |
| `?` | **Schema** | Data types and shapes. |
| `$` | **Annotation** | Important comments, notes, caveats, or rationale. |
| `#` | **Route** | API endpoints (HTTP/RPC). |

## Hierarchy Rules

- **Indentation:** Defines parent-child relationships. Standard increment is 2 spaces.
- **Lists:** Lines starting with `-` or `>` under a sigil are treated as nested properties or logic steps (supports hierarchical Markdown bullets).
- **Blocks:** The `\` character at the end of a line denotes a multi-line block (e.g., for CLI arguments or long descriptions).
