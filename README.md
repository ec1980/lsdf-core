
# L-SDF: Latent-Structured Documentation Format

*Cut AI coding session input token costs significantly on top of prompt caching. Works with Claude Code, Cursor, and Copilot today.*

![LSDF demo](https://github.com/user-attachments/assets/4049c722-a182-42d1-aa94-81f466fc2796)

L-SDF is an **agent-first** documentation format that maps codebases into compact index files AI agents can scan before opening source code — optimized for **token density** rather than human readability.

## Token Economics & ROI

In a typical coding session, source code is re-sent to the API across many turns. L-SDF replaces that with a compact structural map agents can scan first.
 
Example from a typical Python repository (21 files, ~110K tokens of source, ~8K tokens of L-SDF indices), measured over a 50-turn session:
 
| Scenario | Session Cost | Savings with L-SDF |
| --- | --- | --- |
| Source code, no caching | $5.81 | 90% |
| Source code, with prompt caching | $2.03 | 73% |
| **L-SDF indices + caching** | **$0.55** | — |
 
Modern agents (Claude Code, Cursor, Copilot) use prompt caching, so the middle row is the realistic baseline — **L-SDF can cut input token costs by 60–75% on top of caching, depending on how often agents open source files.**

> **Assumptions:** Claude Sonnet input pricing ($3/M tokens, $0.30/M cached read, $3.75/M cache write); 80% prompt-cache hit rate; 20% of turns drill into source for ~10K uncached tokens with L-SDF; and without L-SDF, agents incur an additional 15% raw-source orientation overhead on top of drilldowns. Output tokens identical across scenarios and excluded. Numbers vary with repo size, agent behavior, and model choice. Savings apply to input tokens only; output tokens and tool call costs are not modeled.

## The Philosophy: Agent-First vs. Human-First

Human-first documentation includes prose and formatting valuable to readers, but expensive when repeatedly loaded into AI coding sessions. L-SDF is designed for agents:

* **Sigils as hard anchors:** Symbols like `@`, `!`, and `~` give agents stable structural anchors without inferring meaning from prose.
* **Compact context:** L-SDF fits a repo-level architecture map into a small context window, available before the agent opens any source file.

---

## The Hello World Example

Here is what L-SDF does to a typical Python file. Given `examples/helloworld/hello.py`:

```python
"""Minimal hello-world CLI example.

Usage:
- Call `Greeter().say_hello(name)` to greet one name and return the message.
- Call `Greeter().greet(names)` to greet a list of non-empty names in order.
- Call `run()` to parse command-line arguments and execute the CLI flow.
"""
import sys

DEFAULT_NAME = "World"

class Greeter:
    def say_hello(self, name: str) -> str:
        if not name:
            raise ValueError("Name must not be empty")
        message = f"Hello, {name}!"
        print(message)
        return message

    def greet(self, names: list[str]) -> list[str]:
        return [self.say_hello(n) for n in names if n.strip()]

def parse(argv: list[str]) -> list[str]:
    names = [a.strip() for a in argv if a.strip()]
    return names if names else [DEFAULT_NAME]

def run() -> None:
    Greeter().greet(parse(sys.argv[1:]))

if __name__ == "__main__":
    run()
```

Running `lsdf gen examples/helloworld` produces two index files.

`INDEX.lsdf` — compact navigation map (what exists):

```text
@hello.py
 ~sys
 @Greeter
  !say_hello
  !greet
 !parse
 !run
```

`INDEX.detail.lsdf` — compact contract and call-edge map (how to call it):

```text
@hello.py
 ~sys
 @Greeter
  !say_hello(name:s):s
  !greet(names:[s]):[s] > say_hello
 !parse(argv:[s]):[s]
 !run > Greeter.greet,parse
```

`INDEX.lsdf` keeps only the navigation skeleton. `INDEX.detail.lsdf` adds compact signatures and call edges while still omitting implementation bodies. Module docstrings are not extracted into detail indices, so high-level usage notes can stay in the source file without bloating the agent-facing view. `self` is omitted, `()` is omitted for zero-argument functions, and standard type aliases replace verbose names (`s`=str, `a`=Any, `[s]`=list[str], `q[s]`=Sequence[str], `l[...]`=Literal[...]).

| | Source (`hello.py`) | `INDEX.lsdf` | `INDEX.detail.lsdf` |
| --- | --- | --- | --- |
| Tokens | ~221 | ~15 | ~34 |
| Savings | — | **~15× fewer** | **~6.5× fewer** |

This example uses a very small source file, so the detail index has less room to compress. In a more typical repository, L-SDF index files are often about 10-20x smaller than the source they summarize.

An agent navigating the repo reads `INDEX.lsdf` first. It only opens `INDEX.detail.lsdf` when it needs signatures or call edges, and opens `hello.py` only when it needs the implementation body.

---

## Quick Start

> Status: Draft v1.1 format. Current generator supports Python repositories. Other language generators are welcome.

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
# or, without pytest:
PYTHONPATH=. python3 -m unittest tests.test_core -v
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
    !myapp=src.cli:main
   $lsdf:1.1.0
   ```

* `.lsdf/lsdf_instructions.md`: The protocol instruction for AI agents — loaded into agent config files automatically.
 
  `lsdf init` automatically appends it to any agent config files it finds (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `CONVENTIONS.md`). Files that don't exist are skipped; files that already contain the instructions are left untouched. Re-running `lsdf init` is safe.

   If you add a new agent config file later, re-run `lsdf init` to append the instructions automatically. For agent tools not in the list above, append manually:

   ```bash
   cat .lsdf/lsdf_instructions.md >> <your-agent-config-file>
   ```

* `.lsdf/lsdf_spec.md`: The compact syntax reference agents can consult without loading the full `SPEC.md`.
* `.lsdfignore`: A file to prevent the indexer from wasting tokens on folders like node_modules or `__pycache__`.

If your project's top-level structure or stack changes later, run `lsdf init` again to refresh `project.lsdf`.

To also add a GitHub Actions workflow that auto-regenerates indices on every push, pass `--ci`:

```bash
lsdf init --ci
```

This adds `.github/workflows/update-lsdf.yml`. On every push it installs `lsdf-core` from PyPI, regenerates `INDEX.lsdf` and `INDEX.detail.lsdf` files, and commits any changes back to the branch. Requires GitHub Actions to have write permission on the repository. Re-running `lsdf init --ci` is safe — it will not overwrite an existing workflow.

### 3. Generate Indices

Scan your source code to generate or update `INDEX.lsdf` and `INDEX.detail.lsdf` maps in your source directories.

```bash
lsdf gen . --recursive
```

> Run `lsdf stats` after your first generation to see exactly how much you're saving on your next AI coding session.

---

## Index Drift and Sync

A stale index is worse than no index. If an agent trusts an out-of-date index, it can generate code against the wrong signatures just as confidently as if they were correct. Drift is the failure mode you have to design against.

L-SDF gives you three layers of defense:

**1. Auto-regeneration after each structural edit.**

After any structural edit, the AI agent is instructed to run `lsdf gen <dir>`. You should do the same when making structural edits manually.

**2. `lsdf sync` as an enforcement check.** Run it in CI or as a pre-commit hook:

```bash
lsdf sync . --check
```

The exit code is non-zero if any index file is out of date relative to source. Wire this into your CI’s required checks and stale indices stop reaching `main`.

**3. Auto-regeneration on each push via `lsdf init --ci`.**

This gives you the strongest enforcement, but it requires write permissions on the branch and may create noisy history. Use it in repos where index accuracy matters more than a perfectly clean commit log.

---

## AI Agent Integration

L-SDF works with your existing AI tools by providing them with a "map" to read before they ever touch your source code.

### The Agent Workflow

   1. Read `project.lsdf` at the root.
   2. Read the nearest `INDEX.lsdf` to navigate structure (what exists).
   3. If signatures or contracts are needed, read `INDEX.detail.lsdf` (how to call it, call edges).
   4. Open source files only when implementation bodies are required.
   5. After structural edits, update both index files with `lsdf gen <dir>`.

### Compare Agent Behavior

You can compare agent behavior with and without LSDF guidance.

#### Suggested Prompts

> List the main entry points, pipeline stages, and external dependencies in `src`. Do it once using LSDF files first, and once by reading raw source only. Show the files opened and tokens used in both cases.

> Find all functions in `src` that accept a Pydantic model, TypedDict, or dataclass-like schema as input. Do it with and without LSDF guidance. Show the files opened and tokens used in both cases.

> If we rename a core function in `src`, what other functions, routes, or callers would likely need updates? Answer once using LSDF files first, and once using raw source only. Show the files opened and tokens used in both cases.


---

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
| `$` | **Annotation** | Important comments, notes, docstrings, or rationale. | `# TODO: handle legacy fallback` |
| `#` | **Route** | API endpoint, webhook, or URL path. | `@app.get("/users")` |

*Note: sigils like `#`, `@`, and `!` may resemble host-language syntax, but the overlap is only cosmetic: sigils live in dedicated .lsdf files and are interpreted by the L-SDF format, not by the host language parser.*

> See `SPEC.md` for the full specification.

---

## CLI Commands

* `lsdf init`: Bootstrap a repo for L-SDF.
* `lsdf gen`: Generate or update `INDEX.lsdf` and `INDEX.detail.lsdf` from source code.
* `lsdf sync`: Verify that indices match the current source code.
* `lsdf trans`: Translate `.lsdf` to Markdown.
* `lsdf stats`: Estimate session cost and savings.

> See `docs/CLI.md` for more details.

---

## Current Limitations

* The current generator supports Python repositories.
* The format is Draft v1.1 and may evolve before a stable 2.0 spec.
* Generated call edges are structural hints, not a complete static-analysis call graph.

---

## License

MIT

---

## Contributing

L-SDF is an open standard. We welcome new generators for different languages (Go, Rust, TS.)
