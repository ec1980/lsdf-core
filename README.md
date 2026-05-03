
# L-SDF: Latent-Structured Documentation Format

L-SDF is an **agent-first** documentation format for representing codebases in a compact, structured form that AI coding agents can navigate efficiently. While standard documentation such as Markdown is optimized for human readability, L-SDF is optimized for **token density, inference efficiency, and context awareness**. By using a hierarchical sigil-based topology, L-SDF helps agents like Claude Code, Cursor, and Codex/Copilot map large repositories at a fraction of the token cost of reading raw source files or prose-heavy documentation.

## The Philosophy: Agent-First vs. Human-First

Standard documentation (Markdown) is "chatty" and visual. It wastes thousands of tokens on headers, prose, and formatting that AI agents must "filter out." L-SDF is designed for the Latent Space:

* Sigils as Hard Anchors: In L-SDF, symbols like @, !, and ~ provide unambiguous anchors. The agent doesn't "guess" if a header is a class or a title—it knows with 100% certainty.
* KV-Cache Optimization: L-SDF fits an entire project’s architecture into a single attention window. This keeps the "Latent Map" of the repo "hot" in the model's memory, eliminating hallucinations.
* Logic over Prose: Agents don't need sentences; they need causal chains.

## Token Economics & ROI

In a typical coding session, source code and project context are re-sent to the API with every message. L-SDF indexes raw source code into a compact structural map that an agent can scan first, often using one-tenth the tokens.

Example from a typical Python repository with L-SDF indices:

| Metric | Source Code | L-SDF Indices |
| --- | --- | --- |
| Files | 21 files | 4 files |
| Token Count | 110,737 tokens | 9,535 tokens |
| 50-Turn Session Cost | $16.61 | $1.43 |
| Savings | Base | 91.4% reduction / $15.18 saved |

----

## The Hello World Example

Here is what L-SDF does to a typical Python file. Given `examples/helloworld/hello.py`:

```python
import sys

# Default greeting target when no argument is provided.
DEFAULT_NAME = "World"

class Greeter:
    """Sends personalised greetings to one or more named targets."""

    def say_hello(self, name: str) -> str:
        """Greet a single person and return the formatted message.
        Raises:
            ValueError: If name is an empty string.
        """
        if not name:
            raise ValueError("Name must not be empty")
        message = f"Hello, {name}!"
        print(message)
        return message

    def greet(self, names: list[str]) -> list[str]:
        """Greet every non-empty name in the list in order.
        Empty strings are silently skipped.
        Returns a list of the formatted greeting messages.
        """
        return [self.say_hello(n) for n in names if n.strip()]

def parse(argv: list[str]) -> list[str]:
    """Return the list of names from argv, defaulting to [DEFAULT_NAME].
    Strips whitespace from each argument and drops any blank strings.
    """
    names = [a.strip() for a in argv if a.strip()]
    return names if names else [DEFAULT_NAME]

def run() -> None:
    """Entry point: parse CLI args and greet each name in order."""
    Greeter().greet(parse(sys.argv[1:]))

if __name__ == "__main__":
    run()
```

Running `lsdf gen examples/helloworld` produces `INDEX.lsdf`:

```text
@INDEX:helloworld
@hello.py
 ~[sys]
 @Greeter
  !say_hello(self, name):str
  !greet(self, names):list[str]
 !parse(argv):list[str]
 !run()
```

The index captures the full structure — imports, classes, and all signatures — while stripping every docstring, comment, and implementation body:

| | Source (`hello.py`) | L-SDF Index (`INDEX.lsdf`) |
| --- | --- | --- |
| Tokens | ~320 | ~34 |
| Savings | — | **~10× fewer tokens** |

----

## Quick Start

### 1. Install

#### A. For Users (Global Access)

To use L-SDF across any project on your system, install it as a global utility. This ensures the lsdf command is available regardless of which specific project environment you have active.

Install `pipx` first if you do not already have it. The recommended approach is to use your operating system's package manager. For example, on Ubuntu or Debian:

```bash
sudo apt install pipx
pipx ensurepath
```

Then install the L-SDF CLI tool:

```bash
pipx install lsdf-core
```

Verify the installation:

```bash
lsdf --help
```

#### B. For Contributors (Local Repo / Editable Install)

If you have this repository checked out locally and want changes in your working tree to be reflected immediately in the CLI, install it in editable mode with `pipx`:

```bash
pipx ensurepath
cd ~/github/lsdf-core
# force reinstall even if lsdf-core is already installed
pipx install -e . --force
```

If you want to modify the L-SDF source code or run the test suite:

```bash
conda env create -f environment.yml
conda activate lsdf-dev
pytest tests/
```

### 2. Initialize Any Repo

Now, you can navigate to any other project and bootstrap it with L-SDF support:

```bash
# 1. Move to your target project
cd ~/github/my-other-project

# 2. Initialize (creates .lsdf/, .lsdfignore, and project.lsdf)
lsdf init
```

This creates:

* `project.lsdf`: A high-level root manifest that records the detected stack, important top-level directories, and major frameworks. For example:

   ```text
   ^my-other-project:Python
    @docs:documentation
    @scripts:automation
    @src:main-code
    @tests:test-suite
    ~[Pydantic,Pytest]
   ```

* `.lsdf/lsdf_instructions.md`: The Rosetta Stone for AI agents — explains the L-SDF protocol and how to use it.
  
  `lsdf init` automatically appends it to any agent config files it finds (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`). Files that don't exist are skipped; files that already contain the instructions are left untouched. Re-running `lsdf init` is safe.

   If you add a new agent config file later, re-run `lsdf init` to append the instructions automatically. For agent tools not in the list above, append manually:

   ```bash
   cat .lsdf/lsdf_instructions.md >> <your-agent-config-file>
   ```

* `.lsdfignore`: A file to prevent the indexer from wasting tokens on folders like node_modules or `__pycache__`.

If your project's top-level structure or stack changes later, run `lsdf init` again to refresh `project.lsdf`.

To also add a GitHub Actions workflow that auto-regenerates indices on every push, pass `--ci`:

```bash
lsdf init --ci
```

This adds `.github/workflows/update-lsdf.yml`. On every push it installs `lsdf-core` from PyPI, regenerates all `INDEX.lsdf` files, and commits any changes back to the branch. Requires GitHub Actions to have write permission on the repository. Re-running `lsdf init --ci` is safe — it will not overwrite an existing workflow.

### 3. Generate Indices

Scan your source code to generate or update `INDEX.lsdf` maps in your source directories.

```bash
lsdf gen . --recursive
```

> Run `lsdf stats` after your first generation to see exactly how much you're saving on your next AI coding session.
>
> Run `lsdf sync` to verify that indices match the current source code.

----

## AI Agent Integration

L-SDF works with your existing AI tools by providing them with a "map" to read before they ever touch your source code.

### The Agent Workflow

   1. AI reads `project.lsdf` at the root and `INDEX.lsdf` in each directory.
   2. AI identifies project structure and logic flow in the LSDF file.
   3. AI opens ONLY the specific file if the content of the file is needed.
   4. AI updates `INDEX.lsdf` when it modifies the source code.

### Evaluation Example

You can compare agent behavior with and without LSDF guidance.

#### Claude Code Query

> Count the number of functions in the src dir, with and without using LSDF files. Compare the answers, show the number of files opened and tokens used in both cases in a table.

#### Claude Code Response

> Function count: both methods agree — 219 functions
>
> | Metric | LSDF Method | Source Scan Method |
> | ------ | ----------- | ----------------- |
> | **Function count** | **219** | **219** |
> | Files opened | 3 | 12 |
> | Lines read | 568 | 6,453 |
> | Characters | 25,936 | 230,525 |
> | Estimated tokens (chars ÷ 4) | ~6,484 | ~57,631 |
> | **Token reduction** | — | **~9× more expensive** |
>
> The LSDF indices are complete and accurate — every ! sigil maps exactly to a def in the source. The 9× token savings comes from the LSDF stripping docstrings, comments, implementations, and type annotation bodies, leaving only signatures and structural metadata. The payoff grows further in large repos where only a subset of modules are relevant — LSDF lets you skip loading entire files entirely.

----

## The L-SDF Spec

In L-SDF, sigils act as single-character semantic tags. Instead of wasting tokens on verbose words like class, function, or import, the AI reads a single character and instantly understands the architectural role of the line.

### The L-SDF Sigil Table

| Sigil | Name | Meaning / Purpose | Python Equivalent |
| :---: | :--- | :--- | :--- |
| `^` | **Root** | Project-level stack, global configuration, or environment. | `pyproject.toml` / `env` |
| `@` | **Entity** | A structural boundary like a file, class, module, or service. | `hello.py` / `class User:` |
| `!` | **Function** | Logic flow, method, function, or executable step. | `def login():` |
| `~` | **Dependency** | External requirements, imports, or libraries. | `import requests` |
| `?` | **Schema** | Data types, interfaces, variable shapes, or database models. | `pydantic.BaseModel` |
| `$` | **Annotation** | Important comments, notes, caveats, or rationale. | `# TODO: handle legacy fallback` |
| `#` | **Route** | API endpoint, webhook, or URL path. | `@app.get("/users")` |

> See `SPEC.md` for the full specification.

----

## CLI Commands

* lsdf init: Bootstrap a repo for L-SDF.
* lsdf gen `<path>`: Generate or update .lsdf files from source code.
* lsdf trans `<file>`: Translate `.lsdf` to Markdown or `.md` to L-SDF.
* lsdf sync: Verify that indices match the current source code (CI/CD friendly).
* lsdf stats: Calculate your token ROI and savings.

> See `docs/CLI.md` for more details.

----

## Contributing

L-SDF is an open standard. We welcome new Generators for different languages (Go, Rust, TS) and Translators for new AI IDEs.
