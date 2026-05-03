# 🖥️ LSDF CLI Reference Manual

The `lsdf` command line tool is the reference implementation for generating, validating, and maintaining L-SDF indices.

## Global Options

- `--verbose, -v`: Enable debug logging (useful for seeing which files are skipped).
- `--version`: Show the installed version of `lsdf-core`.

## Commands

- `lsdf init`: Set up project and agent rules.
- `lsdf gen`: Auto-generate indices from source.
- `lsdf trans`: Convert to/from human-readable Markdown.
- `lsdf sync`: Check for drift between source and indices.
- `lsdf stats`: Calculate token savings.

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

Converts between L-SDF and Markdown.

- **Usage:** `lsdf trans <FILE>`
- **Behavior:**
  - If input is `.lsdf` -> outputs Markdown.
  - If input is `.md` -> outputs L-SDF (compressed).
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

Calculates token savings for the project.

- **Usage:** `lsdf stats`
- **Output:** Displays total tokens (Code vs. L-SDF) and estimated API cost savings.
