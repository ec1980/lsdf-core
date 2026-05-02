import click
import os
import json
from importlib.metadata import PackageNotFoundError, version
from .core import to_markdown, from_markdown
from .generators import get_generator

def _package_version():
    try:
        return version("lsdf-core")
    except PackageNotFoundError:
        return "0.0.0"


def _iter_walk_roots(path, recursive, depth):
    root_path = os.path.abspath(path)
    max_depth = None if depth is None else max(depth, 0)

    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = os.path.relpath(os.path.abspath(root), root_path)
        current_depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        yield root, dirs, files, current_depth

        if not recursive:
            dirs[:] = []
        elif max_depth is not None and current_depth >= max_depth:
            dirs[:] = []


def _default_ignored_entries():
    return {".git", "__pycache__", ".pytest_cache", "venv", "node_modules", ".agents", ".vscode", ".github"}


def _build_index_content(root, files, verbose=False, include_comments=False):
    dir_indices = []

    for file in files:
        file_path = os.path.join(root, file)
        generator = get_generator(file)
        if generator:
            if verbose:
                click.echo(f"  generating from {file_path}")
            try:
                content = generator.generate(file_path, include_comments=include_comments)
                if content:
                    dir_indices.append(content)
            except Exception as e:
                click.echo(f"⚠️ Error scanning {file}: {e}")
        elif verbose:
            click.echo(f"  skipping unsupported file {file_path}")

    if not dir_indices:
        return None

    return f"@INDEX:{os.path.basename(root) or 'root'}\n" + "\n".join(dir_indices)


def _detect_stack_markers(project_root):
    markers = []

    if os.path.exists(os.path.join(project_root, "pyproject.toml")):
        markers.append("Python")
    if os.path.exists(os.path.join(project_root, "requirements.txt")):
        markers.append("Python")
    if os.path.exists(os.path.join(project_root, "environment.yml")):
        markers.append("Python")
    if os.path.exists(os.path.join(project_root, "package.json")):
        markers.append("Node")
    if os.path.exists(os.path.join(project_root, "tsconfig.json")):
        markers.append("TypeScript")
    if os.path.exists(os.path.join(project_root, "go.mod")):
        markers.append("Go")
    if os.path.exists(os.path.join(project_root, "Cargo.toml")):
        markers.append("Rust")

    ordered_markers = []
    for marker in markers:
        if marker not in ordered_markers:
            ordered_markers.append(marker)

    return ordered_markers or ["Python"]


def _read_text_if_exists(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _detect_frameworks_and_deps(project_root):
    known_markers = [
        ("fastapi", "FastAPI"),
        ("flask", "Flask"),
        ("django", "Django"),
        ("pydantic", "Pydantic"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pytest", "Pytest"),
        ("click", "Click"),
        ("react", "React"),
        ("next", "Next.js"),
        ("express", "Express"),
        ("vue", "Vue"),
        ("svelte", "Svelte"),
    ]

    detected = []

    pyproject_text = _read_text_if_exists(os.path.join(project_root, "pyproject.toml")) or ""
    requirements_text = _read_text_if_exists(os.path.join(project_root, "requirements.txt")) or ""
    environment_text = _read_text_if_exists(os.path.join(project_root, "environment.yml")) or ""
    package_json_text = _read_text_if_exists(os.path.join(project_root, "package.json")) or ""
    dockerfile_text = _read_text_if_exists(os.path.join(project_root, "Dockerfile")) or ""

    haystacks = [
        pyproject_text.lower(),
        requirements_text.lower(),
        environment_text.lower(),
        package_json_text.lower(),
        dockerfile_text.lower(),
    ]

    for needle, label in known_markers:
        if any(needle in haystack for haystack in haystacks) and label not in detected:
            detected.append(label)

    if package_json_text:
        try:
            package_json = json.loads(package_json_text)
            for field in ("dependencies", "devDependencies"):
                deps = package_json.get(field, {})
                for dep_name in deps:
                    lowered = dep_name.lower()
                    for needle, label in known_markers:
                        if lowered == needle and label not in detected:
                            detected.append(label)
        except json.JSONDecodeError:
            pass

    if "uvicorn" in dockerfile_text.lower() and "FastAPI" not in detected:
        detected.append("FastAPI")
    if "streamlit" in dockerfile_text.lower() and "Streamlit" not in detected:
        detected.append("Streamlit")

    return detected[:5]


def _load_lsdfignore(project_root):
    ignore_path = os.path.join(project_root, ".lsdfignore")
    ignored = set()

    if not os.path.exists(ignore_path):
        return set(_default_ignored_entries())

    try:
        with open(ignore_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                ignored.add(line.rstrip("/"))
    except OSError:
        return set(_default_ignored_entries())

    return ignored


def _is_ignored_path(base_path, current_root, entry, ignored):
    rel_path = os.path.relpath(os.path.join(current_root, entry), base_path)
    rel_path = rel_path.replace(os.sep, "/")
    return entry in ignored or rel_path in ignored


def _detect_top_level_zones(project_root):
    zone_labels = {
        "src": "main-code",
        "app": "application",
        "apps": "applications",
        "backend": "backend",
        "frontend": "frontend",
        "web": "web-client",
        "api": "api",
        "services": "services",
        "packages": "packages",
        "tests": "test-suite",
        "test": "test-suite",
        "docs": "documentation",
        "scripts": "automation",
        "infra": "infrastructure",
        "config": "configuration",
        ".github": "ci-cd",
    }
    ignored = _load_lsdfignore(project_root)
    zones = []

    try:
        entries = sorted(os.listdir(project_root))
    except OSError:
        return zones

    for entry in entries:
        full_path = os.path.join(project_root, entry)
        if entry in ignored or not os.path.isdir(full_path):
            continue
        if entry in zone_labels:
            zones.append((entry, zone_labels[entry]))
        elif os.path.exists(os.path.join(full_path, "__init__.py")):
            zones.append((entry, "source"))

    return zones


def _build_project_manifest(project_root):
    project_name = os.path.basename(os.path.abspath(project_root))
    stack = ",".join(_detect_stack_markers(project_root))
    lines = [f"^{project_name}:{stack}"]

    for directory, role in _detect_top_level_zones(project_root):
        lines.append(f" @{directory}:{role}")

    frameworks = _detect_frameworks_and_deps(project_root)
    if frameworks:
        lines.append(" ~[" + ",".join(frameworks) + "]")

    return "\n".join(lines) + "\n"


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable debug logging.')
@click.version_option(version=_package_version(), prog_name='lsdf')
@click.pass_context
def main(ctx, verbose):
    """L-SDF: The Agent-First Documentation Tool."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

@main.command()
@click.argument('path', default='.')
@click.option('--recursive', '-r', is_flag=True, help='Scan subdirectories')
@click.option('--depth', type=click.IntRange(min=0), help='Limit recursion depth.')
@click.option('--extract-comments', '-e', is_flag=True, help='Extract single-line comments as $ annotations.')
@click.pass_context
def gen(ctx, path, recursive, depth, extract_comments):
    """Scans source code to generate .lsdf indices."""
    verbose = ctx.obj.get("verbose", False)
    base_path = os.path.abspath(path)
    ignored = _load_lsdfignore(base_path)

    for root, dirs, files, current_depth in _iter_walk_roots(path, recursive, depth):
        dirs[:] = [d for d in dirs if not _is_ignored_path(base_path, root, d, ignored)]
        files = [f for f in files if not _is_ignored_path(base_path, root, f, ignored)]
        if verbose:
            click.echo(f"Scanning {root} (depth={current_depth})")

        index_content = _build_index_content(
            root,
            files,
            verbose=verbose,
            include_comments=extract_comments,
        )
        if index_content:
            index_path = os.path.join(root, "INDEX.lsdf")
            with open(index_path, "w") as f:
                f.write(index_content)
            click.echo(f"✅ Created: {index_path}")

@main.command()
@click.argument('file')
@click.option('--output', '-o', help='Output file path')
def trans(file, output):
    """Translates between L-SDF and Markdown."""
    if not os.path.exists(file):
        raise click.ClickException(f"File not found: {file}")

    if not (file.endswith('.lsdf') or file.endswith('.md')):
        raise click.ClickException("Unsupported input type. Use a .lsdf or .md file.")

    with open(file, 'r') as f:
        content = f.read()
    
    result = to_markdown(content) if file.endswith('.lsdf') else from_markdown(content)
    
    if output:
        with open(output, 'w') as f:
            f.write(result)
        click.echo(f"✅ Translated to {output}")
    else:
        click.echo(result)

@main.command()
def init():
    """Bootstraps a repository with L-SDF config and agent rules."""
    import shutil
    from pathlib import Path

    # 1. Setup local project paths
    target_agents_dir = Path(".agents")
    target_agents_dir.mkdir(exist_ok=True)
    
    # 2. Locate the SOURCE templates inside the installed package
    # This finds the .agents folder relative to the cli.py file
    source_dir = Path(__file__).parent.parent / ".agents"
    
    # 3. Create .lsdfignore and project.lsdf
    if not Path(".lsdfignore").exists():
        with Path(".lsdfignore").open("w", encoding="utf-8") as f:
            f.write(
                ".git\n"
                "__pycache__\n"
                ".pytest_cache\n"
                "venv\n"
                "node_modules\n"
                ".agents\n"
                ".vscode\n"
                ".github\n"
            )
    
    project_manifest = _build_project_manifest(str(Path.cwd()))
    with Path("project.lsdf").open("w", encoding="utf-8") as f:
        f.write(project_manifest)

    # 4. Copy the high-fidelity instruction files
    if source_dir.exists():
        copied_files = 0
        skipped_files = 0
        for template in source_dir.glob("*"):
            if template.is_file():
                destination = target_agents_dir / template.name
                if destination.exists():
                    skipped_files += 1
                    continue
                shutil.copy(template, destination)
                copied_files += 1
        click.echo(
            f"✅ L-SDF Initialized. Added {copied_files} agent rule file(s) to {target_agents_dir}/"
            f" and preserved {skipped_files} existing file(s)."
        )
    else:
        # Fallback if templates aren't found in the package path
        click.echo("⚠️  Template source not found. Creating basic placeholder rules.")
        fallback_file = target_agents_dir / "claude_instructions.md"
        if fallback_file.exists():
            click.echo(f"ℹ️ Preserved existing fallback rule: {fallback_file}")
        else:
            with fallback_file.open("w") as f:
                f.write("# L-SDF Protocol\nRead .lsdf files first.")

@main.command()
@click.argument('path', default='.')
@click.option('--check', is_flag=True, help='Return exit code 1 when drift is detected.')
@click.pass_context
def sync(ctx, path, check):
    """Verifies that indices are up-to-date."""
    ignore_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.agents', '.idea', '.vscode'}
    verbose = ctx.obj.get("verbose", False)
    stale_dirs = []

    for root, dirs, files, _ in _iter_walk_roots(path, recursive=True, depth=None):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        py_files = [os.path.join(root, file) for file in files if file.endswith('.py')]
        if not py_files:
            continue

        index_path = os.path.join(root, "INDEX.lsdf")
        if not os.path.exists(index_path):
            stale_dirs.append((root, "missing INDEX.lsdf"))
            continue

        expected_content = _build_index_content(root, files, verbose=False)
        if expected_content is None:
            continue

        with open(index_path, 'r') as f:
            current_content = f.read()

        if current_content.rstrip() != expected_content.rstrip():
            stale_dirs.append((root, "INDEX.lsdf content differs from generated output"))
        elif verbose:
            click.echo(f"✓ Up to date: {root}")

    if stale_dirs:
        click.echo("❌ L-SDF drift detected:")
        for root, reason in stale_dirs:
            click.echo(f" - {root}: {reason}")
        if check:
            raise click.exceptions.Exit(1)
        return

    click.echo("✅ All indices are up to date.")

@main.command()
@click.argument('path', default='.')
def stats(path):
    """Calculates token savings (Source Code vs. L-SDF Indices)."""
    import os
    
    # Configuration
    CHARS_PER_TOKEN = 4
    SOURCE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.cpp', '.c', '.h'}
    IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'node_modules', '.agents', '.idea', '.vscode'}
    
    source_chars = 0
    lsdf_chars = 0
    source_files_count = 0
    lsdf_files_count = 0

    click.echo(f"🔍 Analyzing project density in '{path}'...")

    for root, dirs, files in os.walk(path):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)
            
            try:
                file_size = os.path.getsize(file_path)
                
                if file == "INDEX.lsdf" or file == "project.lsdf":
                    lsdf_chars += file_size
                    lsdf_files_count += 1
                elif ext in SOURCE_EXTENSIONS:
                    source_chars += file_size
                    source_files_count += 1
            except OSError:
                pass # Skip files we can't read/access

    # Calculations
    source_tokens = int(source_chars / CHARS_PER_TOKEN)
    lsdf_tokens = int(lsdf_chars / CHARS_PER_TOKEN)
    
    if source_tokens == 0:
        click.echo("⚠️  No source code found to compare.")
        return

    savings_tokens = source_tokens - lsdf_tokens
    savings_percent = (savings_tokens / source_tokens) * 100
    
    # Estimated Cost Savings (Context Window Reloads)
    # Assumption: $3.00 per 1M tokens (Claude 3.5 Sonnet Input Pricing)
    cost_per_million = 3.00
    cost_1_load = (source_tokens / 1_000_000) * cost_per_million
    cost_lsdf_load = (lsdf_tokens / 1_000_000) * cost_per_million
    savings_50_turns = (cost_1_load - cost_lsdf_load) * 50

    # Output Report
    click.echo("\n📊 L-SDF ROI Report")
    click.echo("========================================")
    click.echo(f"Source Files:      {source_files_count:>6} files  |  {source_tokens:>9,} tokens")
    click.echo(f"L-SDF Indices:     {lsdf_files_count:>6} files  |  {lsdf_tokens:>9,} tokens")
    click.echo("----------------------------------------")
    click.echo(f"📉 Density Reduction:   {savings_percent:.1f}%")
    click.echo(f"💰 Est. Savings (50 turns):  ${savings_50_turns:.2f}")
    click.echo("========================================")


if __name__ == '__main__':
    main()
