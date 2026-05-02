# The L-SDF Spec

Version 1.0

## The L-SDF Sigil Table

| Sigil | Name | Meaning / Purpose | Python Equivalent |
| :---: | :--- | :--- | :--- |
| `^` | **Root** | Project-level stack, global configuration, or environment. | `pyproject.toml` / `env` |
| `@` | **Entity** | A structural boundary like a file, class, module, or service. | `hello.py` / `class User:` |
| `!` | **Function** | Logic flow, method, function, or executable step. | `def login():` |
| `~` | **Dependency** | External requirements, imports, or libraries. | `import requests` |
| `?` | **Schema** | Data types, interfaces, variable shapes, or database models. | `pydantic.BaseModel` |
| `$` | **Annotation** | Important comments, notes, caveats, or rationale. | `# TODO: handle legacy fallback` |
| `#` | **Route** | API endpoint, webhook, or URL path. | `@app.get("/users")` |

## Hierarchy Rules

- **Indentation:** Defines parent-child relationships. Standard increment is 2 spaces.
- **Lists:** Lines starting with `-` or `>` under a sigil are treated as nested properties or logic steps (supports hierarchical Markdown bullets).
- **Blocks:** The `\` character at the end of a line denotes a multi-line block (e.g., for CLI arguments or long descriptions).
