import click
import datetime
import hashlib
import os
import json
from importlib.metadata import PackageNotFoundError, version
from .core import to_markdown
from .generators import get_generator

def _package_version():
    try:
        return version("lsdf-core")
    except PackageNotFoundError:
        return "0.0.0"


def _hash_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _combined_source_hash(file_paths):
    """Stable hash over a set of source files (order-independent)."""
    h = hashlib.sha256()
    for path in sorted(file_paths):
        try:
            with open(path, "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()[:16]


def _find_project_root(start_path):
    """Walk up from start_path to find the directory containing .lsdf/ or project.lsdf.
    Falls back to start_path if neither is found.
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current, ".lsdf")) or \
           os.path.exists(os.path.join(current, "project.lsdf")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(start_path)


def _read_meta(base_path):
    """Read .lsdf/meta.json. Returns None if missing or corrupt."""
    meta_path = os.path.join(base_path, ".lsdf", "meta.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_meta(base_path, meta):
    """Write .lsdf/meta.json, creating .lsdf/ if needed."""
    lsdf_dir = os.path.join(base_path, ".lsdf")
    os.makedirs(lsdf_dir, exist_ok=True)
    meta_path = os.path.join(lsdf_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


LSDF_SECTION_START = "<!-- LSDF:START -->"
LSDF_SECTION_END = "<!-- LSDF:END -->"


def _wrap_lsdf_instructions(instructions_text):
    body = instructions_text.strip()
    if body.startswith(LSDF_SECTION_START) and body.endswith(LSDF_SECTION_END):
        return body + "\n"
    return f"{LSDF_SECTION_START}\n{body}\n{LSDF_SECTION_END}\n"


def _replace_legacy_lsdf_section(existing, replacement_block):
    lines = existing.splitlines(keepends=True)
    idx = next(
        (i for i, l in enumerate(lines) if l.lstrip().startswith("#") and "L-SDF Protocol" in l),
        None,
    )
    if idx is None:
        return None
    heading_level = len(lines[idx]) - len(lines[idx].lstrip("#"))
    end_idx = len(lines)
    for j in range(idx + 1, len(lines)):
        stripped = lines[j].rstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= heading_level:
                end_idx = j
                break
    before = "".join(lines[:idx]).rstrip()
    after = "".join(lines[end_idx:]).lstrip()
    new_content = replacement_block
    if before:
        new_content = before + "\n\n" + new_content
    if after:
        new_content = new_content.rstrip() + "\n\n" + after
    return new_content if new_content.endswith("\n") else new_content + "\n"


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
    return {".git", "__pycache__", ".pytest_cache", "venv", "node_modules", ".lsdf", ".vscode", ".github"}


def _build_index_content(root, files, verbose=False):
    nav_parts, detail_parts = [], []

    for file in files:
        file_path = os.path.join(root, file)
        generator = get_generator(file)
        if generator:
            if verbose:
                click.echo(f"  generating from {file_path}")
            try:
                nav, detail = generator.generate(file_path)
                if nav:
                    nav_parts.append(nav)
                if detail:
                    detail_parts.append(detail)
            except Exception as e:
                click.echo(f"⚠️ Error scanning {file}: {e}")
        elif verbose:
            click.echo(f"  skipping unsupported file {file_path}")

    nav = "\n".join(nav_parts) if nav_parts else None
    detail = "\n".join(detail_parts) if detail_parts else None
    return nav, detail


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


def _version_tuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _read_project_lsdf_version(project_lsdf_path):
    """Return the lsdf-core version recorded in project.lsdf.
    Returns '1.0.0' if the file exists but has no $lsdf: line (pre-1.1 format).
    Returns None if the file does not exist (fresh project).
    """
    if not os.path.exists(project_lsdf_path):
        return None
    try:
        with open(project_lsdf_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("$lsdf:"):
                    return line.strip()[6:]
    except OSError:
        pass
    return "1.0.0"


def _read_entry_points(project_root):
    """Read [project.scripts] entry points from pyproject.toml.
    Returns a list of '!name=module:function' strings.
    """
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        return []
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []

    entries = []
    in_scripts = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[project.scripts]":
            in_scripts = True
            continue
        if in_scripts:
            if stripped.startswith("["):
                break
            if "=" in stripped and not stripped.startswith("#"):
                name, _, target = stripped.partition("=")
                name = name.strip()
                target = target.strip().strip('"').strip("'")
                if name and target:
                    entries.append(f"!{name}={target}")
    return entries


def _build_project_manifest(project_root):
    project_name = os.path.basename(os.path.abspath(project_root))
    stack = ",".join(_detect_stack_markers(project_root))
    lines = [f"^{project_name}:{stack}"]

    for directory, role in _detect_top_level_zones(project_root):
        lines.append(f" @{directory}:{role}")

    frameworks = _detect_frameworks_and_deps(project_root)
    if frameworks:
        lines.append(" ~[" + ",".join(frameworks) + "]")

    for ep in _read_entry_points(project_root):
        lines.append(f" {ep}")

    lines.append(f"$lsdf:{_package_version()}")

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
@click.pass_context
def gen(ctx, path, recursive, depth):
    """Scans source code to generate .lsdf indices."""
    verbose = ctx.obj.get("verbose", False)
    base_path = os.path.abspath(path)
    project_root = _find_project_root(base_path)
    ignored = _load_lsdfignore(project_root)

    meta = _read_meta(project_root) or {"generator": "lsdf-core", "indices": {}}
    meta["version"] = _package_version()
    meta["generated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for root, dirs, files, current_depth in _iter_walk_roots(path, recursive, depth):
        dirs[:] = [d for d in dirs if not _is_ignored_path(project_root, root, d, ignored)]
        files = [f for f in files if not _is_ignored_path(project_root, root, f, ignored)]
        if verbose:
            click.echo(f"Scanning {root} (depth={current_depth})")

        nav, detail = _build_index_content(root, files, verbose=verbose)

        source_files = sorted(
            os.path.relpath(os.path.join(root, f), project_root)
            for f in files if get_generator(f) is not None
        )
        source_hash = _combined_source_hash(
            [os.path.join(project_root, f) for f in source_files]
        )

        if nav:
            index_path = os.path.join(root, "INDEX.lsdf")
            with open(index_path, "w") as f:
                f.write(nav)
            click.echo(f"✅ Created: {index_path}")
            meta["indices"][os.path.relpath(index_path, project_root)] = {
                "profile": "nav",
                "source_files": source_files,
                "source_hash": source_hash,
                "index_hash": _hash_str(nav),
            }
        if detail:
            detail_path = os.path.join(root, "INDEX.detail.lsdf")
            with open(detail_path, "w") as f:
                f.write(detail)
            click.echo(f"✅ Created: {detail_path}")
            meta["indices"][os.path.relpath(detail_path, project_root)] = {
                "profile": "detail",
                "source_files": source_files,
                "source_hash": source_hash,
                "index_hash": _hash_str(detail),
            }

    _write_meta(project_root, meta)

@main.command()
@click.argument('file')
@click.option('--output', '-o', help='Output file path')
def trans(file, output):
    """Translates L-SDF into Markdown."""
    if not os.path.exists(file):
        raise click.ClickException(f"File not found: {file}")

    if not file.endswith('.lsdf'):
        raise click.ClickException("Unsupported input type. Use a .lsdf file.")

    with open(file, 'r') as f:
        content = f.read()
    
    result = to_markdown(content)
    
    if output:
        with open(output, 'w') as f:
            f.write(result)
        click.echo(f"✅ Translated to {output}")
    else:
        click.echo(result)

@main.command()
@click.option('--ci', is_flag=True, help='Add GitHub Actions workflow for auto-updating indices on push.')
def init(ci):
    """Bootstraps a repository with L-SDF config and agent rules."""
    import shutil
    from pathlib import Path

    # 1. Setup local project paths
    target_lsdf_dir = Path(".lsdf")
    target_lsdf_dir.mkdir(exist_ok=True)

    # 2. Locate the SOURCE templates inside the installed package.
    # _templates/ sits alongside cli.py so it's included in the wheel;
    # the repo-root .lsdf/ only works for editable installs.
    source_dir = Path(__file__).parent / "_templates"

    # 3. Detect version for upgrade/downgrade check
    current_version = _package_version()
    project_manifest_exists = Path("project.lsdf").exists()
    stored_version = _read_project_lsdf_version("project.lsdf")
    agent_configs = [
        Path("CLAUDE.md"),
        Path("AGENTS.md"),
        Path(".cursorrules"),
        Path(".github/copilot-instructions.md"),
        Path("CONVENTIONS.md"),
    ]
    missing_manifest_upgrade = False
    if not project_manifest_exists:
        has_lsdf_template_set = any(
            (target_lsdf_dir / name).exists()
            for name in ("lsdf_spec.md", "update-lsdf.yml")
        )
        has_lsdf_protocol_in_agent = False
        for config in agent_configs:
            if config.exists():
                try:
                    config_text = config.read_text(encoding="utf-8")
                    if (
                        LSDF_SECTION_START in config_text or
                        "L-SDF Protocol" in config_text
                    ):
                        has_lsdf_protocol_in_agent = True
                        break
                except OSError:
                    pass
        missing_manifest_upgrade = has_lsdf_template_set or has_lsdf_protocol_in_agent
    is_upgrade = (
        missing_manifest_upgrade or
        (
            stored_version is not None and
            _version_tuple(stored_version) < _version_tuple(current_version)
        )
    )
    is_newer = (
        stored_version is not None and
        _version_tuple(stored_version) > _version_tuple(current_version)
    )
    if missing_manifest_upgrade:
        if has_lsdf_template_set:
            click.echo("⬆️  Rebuilding missing project.lsdf and refreshing existing L-SDF instructions")
        else:
            click.echo("✨ Initializing L-SDF")
    elif is_upgrade:
        click.echo(f"⬆️  Upgrading L-SDF from {stored_version} to {current_version}")
    elif is_newer:
        click.echo(
            f"⚠️  project.lsdf was generated by a newer version of lsdf-core "
            f"({stored_version}) than the installed CLI ({current_version}). "
            f"Templates will not be overwritten. Upgrade the CLI to avoid drift."
        )

    # 4. Create .lsdfignore and project.lsdf
    if not Path(".lsdfignore").exists():
        with Path(".lsdfignore").open("w", encoding="utf-8") as f:
            f.write(
                ".git\n"
                "__pycache__\n"
                ".pytest_cache\n"
                "venv\n"
                "node_modules\n"
                ".lsdf\n"
                ".vscode\n"
                ".github\n"
            )

    project_manifest = _build_project_manifest(str(Path.cwd()))
    with Path("project.lsdf").open("w", encoding="utf-8") as f:
        f.write(project_manifest)

    # 5. Copy template files into .lsdf/ (overwrite on upgrade)
    if source_dir.exists():
        created_files = []
        updated_files = []
        skipped_files = 0
        for template in source_dir.glob("*"):
            if template.is_file():
                destination = target_lsdf_dir / template.name
                try:
                    if template.resolve() == destination.resolve():
                        skipped_files += 1
                        continue
                except OSError:
                    pass
                if destination.exists() and (not is_upgrade or is_newer):
                    skipped_files += 1
                    continue
                existed = destination.exists()
                shutil.copy(template, destination)
                if existed:
                    updated_files.append(destination.name)
                else:
                    created_files.append(destination.name)
        for name in sorted(created_files):
            click.echo(f"✅ Created .lsdf/{name}")
        for name in sorted(updated_files):
            click.echo(f"✅ Updated .lsdf/{name}")
    else:
        click.echo("⚠️  Template source not found. Creating basic placeholder rules.")
        fallback_file = target_lsdf_dir / "lsdf_instructions.md"
        if fallback_file.exists():
            click.echo(f"ℹ️ Preserved existing fallback rule: {fallback_file}")
        else:
            with fallback_file.open("w") as f:
                f.write("# L-SDF Protocol\nRead .lsdf files first.")

    # 6. Optionally deploy GitHub Actions workflow from .lsdf/ to .github/workflows/
    if ci:
        workflow_src = target_lsdf_dir / "update-lsdf.yml"
        workflow_dst = Path(".github/workflows/update-lsdf.yml")
        if not workflow_src.exists():
            click.echo("⚠️  Workflow template not found in package.")
        else:
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            if workflow_dst.exists():
                click.echo(f"ℹ️  Skipped {workflow_dst} (already exists)")
            else:
                shutil.copy(workflow_src, workflow_dst)
                click.echo(f"✅ Added GitHub Actions workflow to {workflow_dst}")

    # 7. Append instructions to any agent config files that already exist
    instructions_path = target_lsdf_dir / "lsdf_instructions.md"
    if instructions_path.exists():
        instructions_text = instructions_path.read_text(encoding="utf-8")
        managed_block = _wrap_lsdf_instructions(instructions_text)
        for config in agent_configs:
            if not config.exists():
                continue
            existing = config.read_text(encoding="utf-8")
            if LSDF_SECTION_START in existing and LSDF_SECTION_END in existing:
                if is_upgrade:
                    start_idx = existing.index(LSDF_SECTION_START)
                    end_idx = existing.index(LSDF_SECTION_END) + len(LSDF_SECTION_END)
                    before = existing[:start_idx].rstrip()
                    after = existing[end_idx:].lstrip()
                    new_content = managed_block
                    if before:
                        new_content = before + "\n\n" + new_content
                    if after:
                        new_content = new_content.rstrip() + "\n\n" + after
                    if not new_content.endswith("\n"):
                        new_content += "\n"
                    config.write_text(new_content, encoding="utf-8")
                    click.echo(f"✅ Updated L-SDF instructions in {config}")
                else:
                    click.echo(f"ℹ️  Skipped {config} (L-SDF already present)")
            elif "L-SDF Protocol" in existing:
                if is_upgrade:
                    migrated = _replace_legacy_lsdf_section(existing, managed_block)
                    if migrated is not None:
                        config.write_text(migrated, encoding="utf-8")
                        click.echo(f"✅ Updated L-SDF instructions in {config}")
                else:
                    click.echo(f"ℹ️  Skipped {config} (L-SDF already present)")
            else:
                with config.open("a", encoding="utf-8") as f:
                    if existing and not existing.endswith("\n"):
                        f.write("\n")
                    f.write("\n" + managed_block)
                click.echo(f"✅ Appended L-SDF instructions to {config}")

@main.command()
@click.argument('path', default='.')
@click.option('--check', is_flag=True, help='Return exit code 1 when drift is detected.')
@click.pass_context
def sync(ctx, path, check):
    """Verifies that indices are up-to-date."""
    verbose = ctx.obj.get("verbose", False)
    base_path = os.path.abspath(path)
    project_root = _find_project_root(base_path)
    ignored = _load_lsdfignore(project_root)
    stale_dirs = []

    meta = _read_meta(project_root)

    for root, dirs, files, _ in _iter_walk_roots(path, recursive=True, depth=None):
        dirs[:] = [d for d in dirs if not _is_ignored_path(project_root, root, d, ignored)]
        files = [f for f in files if not _is_ignored_path(project_root, root, f, ignored)]
        py_files = [os.path.join(root, file) for file in files if file.endswith('.py')]
        if not py_files:
            continue

        nav_path = os.path.join(root, "INDEX.lsdf")
        detail_path = os.path.join(root, "INDEX.detail.lsdf")
        nav_rel = os.path.relpath(nav_path, project_root)
        detail_rel = os.path.relpath(detail_path, project_root)
        nav_meta = meta.get("indices", {}).get(nav_rel) if meta else None
        detail_meta = meta.get("indices", {}).get(detail_rel) if meta else None

        if nav_meta:
            # Fast path: hash-based staleness check
            if not os.path.exists(nav_path):
                stale_dirs.append((root, "missing INDEX.lsdf"))
                continue
            abs_sources = [os.path.join(project_root, f) for f in nav_meta["source_files"]]
            if _combined_source_hash(abs_sources) != nav_meta["source_hash"]:
                stale_dirs.append((root, "INDEX.lsdf is stale (source changed)"))
                continue
            with open(nav_path, "r", encoding="utf-8") as f:
                if _hash_str(f.read().rstrip()) != nav_meta["index_hash"]:
                    stale_dirs.append((root, "INDEX.lsdf has been modified"))
                    continue
            if detail_meta and os.path.exists(detail_path):
                abs_sources = [os.path.join(project_root, f) for f in detail_meta["source_files"]]
                if _combined_source_hash(abs_sources) != detail_meta["source_hash"]:
                    stale_dirs.append((root, "INDEX.detail.lsdf is stale (source changed)"))
                    continue
                with open(detail_path, "r", encoding="utf-8") as f:
                    if _hash_str(f.read().rstrip()) != detail_meta["index_hash"]:
                        stale_dirs.append((root, "INDEX.detail.lsdf has been modified"))
                        continue
            if verbose:
                click.echo(f"✓ Up to date: {root}")
        else:
            # Slow path: full content regeneration
            if not os.path.exists(nav_path):
                stale_dirs.append((root, "missing INDEX.lsdf"))
                continue
            with open(nav_path, "r") as f:
                current_nav = f.read()
            expected_nav, expected_detail = _build_index_content(root, files, verbose=False)
            if expected_nav is None:
                continue
            if current_nav.rstrip() != expected_nav.rstrip():
                stale_dirs.append((root, "INDEX.lsdf content differs from generated output"))
                continue
            if os.path.exists(detail_path) and expected_detail:
                with open(detail_path, "r") as f:
                    current_detail = f.read()
                if current_detail.rstrip() != expected_detail.rstrip():
                    stale_dirs.append((root, "INDEX.detail.lsdf content differs from generated output"))
                    continue
            if verbose:
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
@click.option('--price', type=float, default=3.0, show_default=True,
              help='Input token cost per million tokens.')
@click.option('--turns', type=click.IntRange(min=1), default=50, show_default=True,
              help='Turns per coding session.')
@click.option('--cache_hit_rate', type=click.FloatRange(min=0.0, max=1.0), default=0.8, show_default=True,
              help='Fraction of cached reads served from cache.')
@click.option('--dd', type=click.FloatRange(min=0.0, max=1.0), default=0.2, show_default=True,
              help='Fraction of turns that drill into raw source.')
@click.option('--verbose', is_flag=True, help='Print model assumptions.')
def stats(path, price, turns, cache_hit_rate, dd, verbose):
    """Calculates token savings (Source Code vs. L-SDF Indices)."""

    # ── Model configuration ──────────────────────────────────────────────────
    SOURCE_EXTENSIONS  = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs',
                          '.java', '.cpp', '.c', '.h'}
    IGNORE_DIRS        = {'.git', '__pycache__', 'venv', 'node_modules',
                          '.lsdf', '.idea', '.vscode'}
    CHARS_PER_TOKEN    = 4      # approximate chars per token
    ORIENTATION_RATE   = 0.15   # source-open overhead without L-SDF
    DETAIL_OPEN_RATE   = 0.20   # fraction of turns that read INDEX.detail.lsdf
    DRILLDOWN_TOKENS   = 10_000 # uncached source tokens per drilldown
    CACHE_READ_RATIO   = 0.10   # cache read price as fraction of input price
    CACHE_WRITE_RATIO  = 1.25   # cache write price as fraction of input price
    # ─────────────────────────────────────────────────────────────────────────

    source_chars = 0
    nav_chars = 0
    detail_chars = 0
    source_files_count = 0
    nav_files_count = 0
    detail_files_count = 0

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)
            try:
                file_size = os.path.getsize(file_path)
                if file in ("INDEX.lsdf", "project.lsdf"):
                    nav_chars += file_size
                    nav_files_count += 1
                elif file == "INDEX.detail.lsdf":
                    detail_chars += file_size
                    detail_files_count += 1
                elif ext in SOURCE_EXTENSIONS:
                    source_chars += file_size
                    source_files_count += 1
            except OSError:
                pass

    source_tokens = source_chars // CHARS_PER_TOKEN
    nav_tokens    = nav_chars    // CHARS_PER_TOKEN
    detail_tokens = detail_chars // CHARS_PER_TOKEN

    if source_tokens == 0:
        click.echo("⚠️  No source code found to compare.")
        return

    cache_read_price = price * CACHE_READ_RATIO
    cache_write_price = price * CACHE_WRITE_RATIO
    source_open_rate = dd + ORIENTATION_RATE

    def cached_session_cost(tokens):
        """One cache write, then turns-1 blended cache accesses."""
        if tokens <= 0:
            return 0.0
        return tokens * (
            cache_write_price
            + max(turns - 1, 0) * (cache_write_price * (1 - cache_hit_rate) + cache_read_price * cache_hit_rate)
        ) / 1_000_000

    cost_a = turns * source_tokens * source_open_rate * price / 1_000_000
    cost_b = source_tokens * source_open_rate * (
        cache_write_price
        + max(turns - 1, 0) * (cache_write_price * (1 - cache_hit_rate) + cache_read_price * cache_hit_rate)
    ) / 1_000_000
    cost_c = (
        cached_session_cost(nav_tokens)
        + cached_session_cost(detail_tokens * DETAIL_OPEN_RATE)
        + turns * dd * DRILLDOWN_TOKENS * price / 1_000_000
    )
    sav_b = (1 - cost_c / cost_b) * 100 if cost_b > 0 else 0.0
    lsdf_tokens = nav_tokens + detail_tokens
    ratio = source_tokens / lsdf_tokens if lsdf_tokens > 0 else 0.0

    W = 55
    LBL_W = 32  # supports up to "INDEX.detail.lsdf (1000 files)"
    VAL_W = 9   # supports up to 1,000,000 tokens
    SEP_D = click.style("═" * W, fg="yellow")
    SEP_S = "─" * W

    def tok_row(label, tokens):
        val = click.style(f"{tokens:>{VAL_W},}", fg="blue")
        return f"  {label:<{LBL_W}}│  {val} tokens"

    click.echo(SEP_D)
    click.echo(click.style("  L-SDF session savings estimate", fg="yellow"))
    click.echo(SEP_S)
    click.echo(tok_row(f"Source files ({source_files_count} files)", source_tokens))
    click.echo(tok_row(f"INDEX.lsdf ({nav_files_count} files)", nav_tokens))
    click.echo(tok_row(f"INDEX.detail.lsdf ({detail_files_count} files)", detail_tokens))
    click.echo(tok_row("Total L-SDF", lsdf_tokens))
    ratio_val = click.style(f"{ratio:>{VAL_W - 1}.1f}×", fg="green")
    click.echo(f"  {'Compression ratio':<{LBL_W}}│  {ratio_val}")
    click.echo(SEP_S)
    click.echo(f"  Est. {turns}-turn session cost")
    cost_col = W - 2
    def cost_row(label, plain, styled):
        line = f"    {label}"
        padding = " " * max(1, cost_col - len(line) - len(plain))
        return line + padding + styled
    click.echo(cost_row("Raw source (cached):", f"${cost_b:.2f}", click.style(f"${cost_b:.2f}", fg="blue")))
    click.echo(cost_row("With L-SDF + caching:", f"${cost_c:.2f}", click.style(f"${cost_c:.2f}", fg="green")))
    click.echo(cost_row("Savings:", f"{sav_b:.0f}%", click.style(f"{sav_b:.0f}%", fg="green")))
    click.echo(SEP_D)
    click.echo("  Run with --verbose to show assumptions.")

    if verbose:
        click.echo()
        click.echo("Assumptions:")
        click.echo(f"  Turns per session:   {turns}")
        click.echo(f"  Chars per token:     {CHARS_PER_TOKEN}")
        click.echo(f"  Drilldowns:          {dd*100:.0f}% of turns require uncached raw-source reads with L-SDF")
        click.echo(f"  Detail open rate:    {DETAIL_OPEN_RATE*100:.0f}% of turns read INDEX.detail.lsdf")
        click.echo(f"  Source overhead:     +{ORIENTATION_RATE*100:.0f}% extra uncached raw-source reads on top of drilldowns, without L-SDF")
        click.echo(f"  Drilldown size:      {DRILLDOWN_TOKENS:,} tokens per uncached source read")
        click.echo(f"  Cache hit rate:      {cache_hit_rate*100:.0f}%")
        click.echo()
        click.echo(f"  Price per M tokens:  ${price:.2f}")
        click.echo(f"  Cache read price:    ${cache_read_price:.2f} ({CACHE_READ_RATIO*100:.0f}% of Price)")
        click.echo(f"  Cache write price:   ${cache_write_price:.2f} ({CACHE_WRITE_RATIO*100:.0f}% of Price)")


if __name__ == '__main__':
    main()
