# 🖥️ LSDF CLI Reference Manual

The `lsdf` command line tool is the reference implementation for generating, validating, and maintaining L-SDF indices.

## Global Options

- `--verbose, -v`: Enable debug logging (useful for seeing which files are skipped).
- `--version`: Show the installed version of `lsdf-core`.

## Commands

- `lsdf init`: Setup project and agent rules.
- `lsdf gen [path]`: Auto-generate indices from source.
- `lsdf trans [file]`: Convert to/from human-readable Markdown.
- `lsdf sync`: Check for drift (CI/CD).
- `lsdf stats`: Calculate token savings.

### 1. `lsdf init`

Bootstraps the current directory with L-SDF configuration.

- **Usage:** `lsdf init [OPTIONS]`
- **Action:**
  - Creates `.lsdfignore` (defaulting to node_modules, __pycache__, .git).
  - Creates `project.lsdf` with the root `^` sigil.
  - Creates `.agents/` folder with AI instruction files without overwriting files that already exist there.

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

### 4. `lsdf sync` (CI/CD Mode)

Verifies that indices are up-to-date. Intended for Git Hooks or GitHub Actions.

- **Usage:** `lsdf sync --check`
- **Behavior:** Returns exit code `1` if a directory with Python files is missing `INDEX.lsdf`, or if the generated index content differs from the current file.

### 5. `lsdf stats` (ROI Calculator)

Calculates token savings for the project.

- **Usage:** `lsdf stats`
- **Output:** Displays total tokens (Code vs. L-SDF) and estimated API cost savings.
