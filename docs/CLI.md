# 🖥️ LSDF CLI Reference Manual

The `lsdf` command line tool is the reference implementation for generating, validating, and maintaining L-SDF indices.

## Global Options

- `--verbose, -v`: Enable debug logging (useful for seeing which files are skipped).
- `--version`: Show the installed version of `lsdf-core`.

## Commands

- `lsdf init`: Set up project and agent rules.
- `lsdf gen`: Auto-generate indices from source.
- `lsdf trans`: Convert L-SDF into human-readable Markdown.
- `lsdf sync`: Check for drift between source and indices.
- `lsdf stats`: Estimate session cost and savings.

### 1. `lsdf init`

Bootstraps the current directory with L-SDF configuration.

- **Usage:** `lsdf init [OPTIONS]`
- **Action:**
  - Creates `.lsdfignore` (defaulting to node_modules, `__pycache__`, .git).
  - Creates `project.lsdf` with the root `^` sigil.
  - Creates `.lsdf/` folder with AI instruction files, without overwriting files that already exist.
  - Appends L-SDF instructions to any agent config files found (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, etc.).
- **Options:**
  - `--ci`: Add a GitHub Actions workflow (`.github/workflows/update-lsdf.yml`) that regenerates indices on every push. Safe to re-run — will not overwrite an existing workflow.

### 2. `lsdf gen` (Generate)

Scans source code to build or update `INDEX.lsdf` files.

- **Usage:** `lsdf gen [PATH] [OPTIONS]`
- **Arguments:**
  - `PATH`: The directory to scan (default: `.`).
- **Options:**
  - `--recursive, -r`: Scan all subdirectories recursively.
  - `--depth <int>`: Limit recursion depth (default: infinite).
  - `--extract-comments, -e`: Extract single-line comments as `$` annotations.
- **Example:**
  
  ```bash
  lsdf gen ./src --recursive --depth 2
  ```

### 3. `lsdf trans` (Translate)

Converts L-SDF into Markdown.

- **Usage:** `lsdf trans <FILE>`
- **Behavior:**
  - Input must be `.lsdf`.
  - Outputs Markdown to stdout by default.
  - Any other file type returns an error.
  - Missing input files return a non-zero exit code.
- **Options:**
  - `--output, -o <FILE>`: Write to file instead of stdout.
- **Example:**
  
  ```bash
  # View as human-readable MD
  lsdf trans src/auth/INDEX.lsdf | less
  ```

### 4. `lsdf sync` (Sync)

Verifies that indices are up-to-date.

- **Usage:** `lsdf sync [PATH] [OPTIONS]`
- **Arguments:**
  - `PATH`: The directory to scan (default: `.`).
- **Options:**
  - `--check`: Return exit code `1` when drift is detected. Intended for Git hooks or GitHub Actions.
- **Behavior:** Reports any directories with Python files that are missing `INDEX.lsdf`, or where the index content differs from the current source.

### 5. `lsdf stats` (ROI Calculator)

Estimates session cost for raw-source versus L-SDF-guided coding.

- **Usage:** `lsdf stats [PATH] [OPTIONS]`
- **Options:**
  - `--price FLOAT`: Input token cost per million tokens (default: `3.0`)
  - `--turns INTEGER`: Turns per coding session (default: `50`)
  - `--cache_hit_rate FLOAT`: Fraction of cached reads served from cache (default: `0.8`)
  - `--dd FLOAT`: Fraction of turns that drill into raw source (default: `0.2`)
  - `--verbose`: Print model assumptions and derived prices
- **Output:** Displays a terminal-friendly session cost report for:
  - `Baseline A`: raw source, no caching
  - `Baseline B`: raw source, with cache
  - `L-SDF+cache`: cached `INDEX.lsdf` plus partial `INDEX.detail.lsdf` reads and uncached source drilldowns
- **Verbose assumptions:** Includes turns per session, chars per token, drilldown rate, detail open rate, source overhead without L-SDF, drilldown size, cache hit rate, and pricing assumptions.
