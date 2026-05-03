import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core import from_markdown, to_markdown
from src.generators.python import PythonGenerator

class TestLSDF(unittest.TestCase):
    def test_translation(self):
        lsdf = "^Test\n@INDEX:repo\n@User\n !login"
        md = to_markdown(lsdf)
        self.assertIn("# Project: Test", md)
        self.assertIn("# DIR: repo", md)
        self.assertIn("## Class: User", md)
        self.assertIn("  - **Function:** login", md)

    def test_translation_labels_class_with_bases_as_class(self):
        lsdf = "@UpdatePolicy(BaseModel)"
        md = to_markdown(lsdf)
        self.assertIn("## Class: UpdatePolicy(BaseModel)", md)

    def test_to_markdown_preserves_nested_hierarchy(self):
        lsdf = "^Test\n@User\n @helpers.py\n !login\n  ?Credentials\n  - validate input"
        md = to_markdown(lsdf)
        self.assertIn("# Project: Test", md)
        self.assertIn("## Class: User", md)
        self.assertIn("  - **File:** helpers.py", md)
        self.assertIn("  - **Function:** login", md)
        self.assertIn("    - **Schema:** Credentials", md)
        self.assertIn("    - validate input", md)

    def test_from_markdown_headers_and_lists(self):
        md = "# Project: Test\n# DIR: repo\n## Class: User\n### Action: login\n- validate input"
        lsdf = from_markdown(md)
        self.assertIn("^Test", lsdf)
        self.assertIn("@INDEX:repo", lsdf)
        self.assertIn("@User", lsdf)
        self.assertIn("!login", lsdf)
        self.assertIn("- validate input", lsdf)

    def test_from_markdown_accepts_function_label(self):
        md = "# Project: Test\n## File: user.py\n### Function: login\n- validate input"
        lsdf = from_markdown(md)
        self.assertIn("^Test", lsdf)
        self.assertIn("@user.py", lsdf)
        self.assertIn("!login", lsdf)

    def test_from_markdown_emphasis_and_code_blocks(self):
        md = "**Dependencies:** requests, click\n```python\nprint('hi')\n```"
        lsdf = from_markdown(md)
        self.assertIn("~requests, click", lsdf)
        self.assertIn("\\print('hi')", lsdf)

    def test_from_markdown_nested_semantic_bullets(self):
        md = "# Project: Test\n## Module: user\n  - **Class:** User\n    - **Function:** login"
        lsdf = from_markdown(md)
        self.assertIn("^Test", lsdf)
        self.assertIn("@user", lsdf)
        self.assertIn("@User", lsdf)
        self.assertIn("  !login", lsdf)

    def test_from_markdown_accepts_file_and_class_labels(self):
        md = "# Project: Test\n## File: poly.py\n  - **Class:** Polygon"
        lsdf = from_markdown(md)
        self.assertIn("@poly.py", lsdf)
        self.assertIn(" @Polygon", lsdf)

    def test_translation_maps_index_to_dir_heading(self):
        md = to_markdown("@INDEX:deal_scorer")
        self.assertIn("# DIR: deal_scorer", md)

    def test_python_generator_produces_two_tier_output(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "import os\n"
                "import os.path\n"
                "from package.module import Thing, helper\n"
                "\n"
                "class FeatureSpec(BaseModel):\n"
                "    feature_id: str\n"
                "    enabled: bool\n"
                "\n"
                "class Greeter:\n"
                "    class Formatter:\n"
                "        def format_name(self, name: str) -> str:\n"
                "            return name.title()\n"
                "\n"
                "    def say_hello(self, name: str) -> str:\n"
                "        return f'Hello {name}'\n"
                "\n"
                "def run_loop(user=None):\n"
                "    return user\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))

            # Both tiers share the file header and imports
            for output in (nav, detail):
                self.assertIn("@sample.py", output)
                self.assertIn(" ~os,os.path", output)
                self.assertIn(" ~package.module:Thing,helper", output)
                self.assertNotIn("~[", output)

            # Nav: schema classes use ? sigil; regular classes use @
            self.assertIn(" ?FeatureSpec", nav)
            self.assertNotIn("@FeatureSpec", nav)
            self.assertIn(" @Greeter", nav)
            self.assertIn("  @Formatter", nav)
            self.assertIn("   !format_name", nav)
            self.assertIn("  !say_hello", nav)
            self.assertIn(" !run_loop", nav)
            self.assertNotIn("(self,", nav)
            self.assertNotIn(":str", nav)

            # Detail: schema class emitted as inline ?Name{fields}
            self.assertIn(" ?FeatureSpec{feature_id:s,enabled:b}", detail)
            self.assertNotIn("@FeatureSpec", detail)
            self.assertIn("   !format_name(name:s):s", detail)
            self.assertIn("  !say_hello(name:s):s", detail)
            self.assertIn(" !run_loop(user)", detail)
            self.assertNotIn("self", detail)

    def test_python_generator_omits_none_return_annotation(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "def test_func(tmp_path) -> None:\n"
                "    return None\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertIn("!test_func", nav)
            self.assertIn("!test_func(tmp_path)", detail)
            self.assertNotIn(":None", nav)
            self.assertNotIn(":None", detail)

    def test_python_generator_compact_import_syntax(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from deal_scorer.cli import main\n",
                encoding="utf-8",
            )

            nav, _ = PythonGenerator().generate(str(file_path))
            self.assertIn(" ~deal_scorer.cli:main", nav)
            self.assertNotIn("~[", nav)
            self.assertNotIn("{main}", nav)

    def test_python_generator_extracts_routes_from_decorators(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from fastapi import APIRouter\n"
                "router = APIRouter()\n"
                "\n"
                '@router.get("/health")\n'
                "def health_check():\n"
                "    return {'ok': True}\n"
                "\n"
                '@router.post("/items")\n'
                "def create_item(item):\n"
                "    return item\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))
            # Nav: names only, no routes
            self.assertIn(" !health_check", nav)
            self.assertIn(" !create_item", nav)
            # Detail: signatures and routes
            self.assertIn(" !health_check", detail)
            self.assertIn("  #GET /health", detail)
            self.assertIn(" !create_item(item)", detail)
            self.assertIn("  #POST /items", detail)

    def test_python_generator_type_aliases(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from typing import Optional\n"
                "\n"
                "def process(name: str, count: int, active: bool) -> float:\n"
                "    return 1.0\n"
                "\n"
                "def load(items: list[str]) -> dict[str, int]:\n"
                "    return {}\n"
                "\n"
                "def maybe(val: Optional[str]) -> str | None:\n"
                "    return val\n",
                encoding="utf-8",
            )

            _, detail = PythonGenerator().generate(str(file_path))
            self.assertIn("!process(name:s,count:i,active:b):f", detail)
            self.assertIn("!load(items:[s]):{s:i}", detail)
            self.assertIn("!maybe(val:s?)", detail)
            self.assertIn(":s?", detail)

    def test_python_generator_call_edges(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "class Greeter:\n"
                "    def say_hello(self, name):\n"
                "        return f'Hello {name}'\n"
                "    def greet(self, names):\n"
                "        return [self.say_hello(n) for n in names]\n"
                "\n"
                "def parse(argv):\n"
                "    return argv\n"
                "\n"
                "def run():\n"
                "    Greeter().greet(parse([]))\n",
                encoding="utf-8",
            )

            _, detail = PythonGenerator().generate(str(file_path))
            self.assertIn("!greet(names) > say_hello", detail)
            self.assertIn("!run > Greeter.greet,parse", detail)

    def test_python_generator_inline_schema(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from dataclasses import dataclass\n"
                "from pydantic import BaseModel\n"
                "\n"
                "class User(BaseModel):\n"
                "    id: int\n"
                "    email: str\n"
                "    active: bool\n"
                "\n"
                "@dataclass\n"
                "class Point:\n"
                "    x: float\n"
                "    y: float\n"
                "\n"
                "class Service:\n"
                "    def run(self):\n"
                "        pass\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))

            # Schema classes use ? in nav (name only)
            self.assertIn(" ?User", nav)
            self.assertIn(" ?Point", nav)
            self.assertNotIn("@User", nav)
            self.assertNotIn("@Point", nav)
            # Non-schema class still uses @
            self.assertIn(" @Service", nav)

            # Schema classes use inline ? form in detail
            self.assertIn(" ?User{id:i,email:s,active:b}", detail)
            self.assertIn(" ?Point{x:f,y:f}", detail)
            self.assertNotIn("@User", detail)
            self.assertNotIn("@Point", detail)
            # Non-schema class still uses @
            self.assertIn(" @Service", detail)

    def test_python_generator_schema_multiline_fallback(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            # Schema with many fields that won't fit on one line
            fields = "\n".join(f"    field_{i}: str" for i in range(15))
            file_path.write_text(
                f"from pydantic import BaseModel\n\nclass Big(BaseModel):\n{fields}\n",
                encoding="utf-8",
            )

            _, detail = PythonGenerator().generate(str(file_path))

            # One-line would exceed budget — should fall back to multiline
            self.assertNotIn("?Big{", detail)
            self.assertIn("?Big", detail)
            self.assertIn(" ?field_0:s", detail)

    def test_python_generator_skips_low_value_symbols(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "import pytest\n"
                "\n"
                "class User:\n"
                "    def __init__(self):\n"
                "        self.x = 1\n"
                "    def _validate(self):\n"
                "        return True\n"
                "    @property\n"
                "    def name(self):\n"
                "        return self.x\n"
                "    @name.setter\n"
                "    def name(self, val):\n"
                "        self.x = val\n"
                "    def public_method(self):\n"
                "        return self.x\n"
                "\n"
                "@pytest.fixture\n"
                "def my_fixture():\n"
                "    return User()\n"
                "\n"
                "def _helper():\n"
                "    pass\n"
                "\n"
                "def public_fn():\n"
                "    pass\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))
            for output in (nav, detail):
                self.assertNotIn("__init__", output)
                self.assertNotIn("_validate", output)
                self.assertNotIn("!name", output)        # property accessor
                self.assertNotIn("my_fixture", output)
                self.assertNotIn("_helper", output)
                self.assertIn("!public_method", output)
                self.assertIn("!public_fn", output)

    def test_python_generator_omits_dunders(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "class Foo:\n"
                "    def __init__(self):\n"
                "        self.x = 1\n"
                "    def __repr__(self):\n"
                "        return 'Foo'\n"
                "    def real_method(self):\n"
                "        return self.x\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertNotIn("__init__", nav)
            self.assertNotIn("__repr__", nav)
            self.assertNotIn("__init__", detail)
            self.assertNotIn("__repr__", detail)
            self.assertIn("!real_method", nav)
            self.assertIn("!real_method", detail)


class TestCLI(unittest.TestCase):
    def setUp(self):
        from click.testing import CliRunner
        from src.cli import main

        self.runner = CliRunner()
        self.main = main

    def test_gen_produces_both_index_tiers(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "app.py").write_text(
                "def run():\n    return 1\n",
                encoding="utf-8",
            )

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((pkg / "INDEX.lsdf").exists())
            self.assertTrue((pkg / "INDEX.detail.lsdf").exists())

            nav = (pkg / "INDEX.lsdf").read_text(encoding="utf-8")
            detail = (pkg / "INDEX.detail.lsdf").read_text(encoding="utf-8")
            self.assertIn("@app.py", nav)
            self.assertIn(" !run", nav)
            self.assertNotIn("@INDEX:", nav)
            self.assertIn("@app.py", detail)
            self.assertIn(" !run", detail)

    def test_gen_supports_depth_and_overwrite_default(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / "src"
            nested = src / "nested"
            src.mkdir()
            nested.mkdir()

            (src / "app.py").write_text("def top():\n    return 1\n", encoding="utf-8")
            (nested / "child.py").write_text("def child():\n    return 2\n", encoding="utf-8")

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive", "--depth", "1"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((src / "INDEX.lsdf").exists())
            self.assertFalse((nested / "INDEX.lsdf").exists())
            nav = (src / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertIn("@app.py", nav)
            self.assertIn(" !top", nav)

            (src / "INDEX.lsdf").write_text("manual edit\n", encoding="utf-8")
            rewritten = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(rewritten.exit_code, 0, rewritten.output)
            self.assertNotEqual((src / "INDEX.lsdf").read_text(encoding="utf-8"), "manual edit\n")

    def test_gen_sorts_files_alphabetically(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()

            (pkg / "zeta.py").write_text("def zeta():\n    return 1\n", encoding="utf-8")
            (pkg / "alpha.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(result.exit_code, 0, result.output)

            nav = (pkg / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertLess(nav.find("@alpha.py"), nav.find("@zeta.py"))

    def test_gen_respects_lsdfignore(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            Path(root / ".lsdfignore").write_text("ignored_dir\n", encoding="utf-8")
            kept = root / "kept"
            ignored = root / "ignored_dir"
            kept.mkdir()
            ignored.mkdir()

            (kept / "keep.py").write_text("def keep():\n    return 1\n", encoding="utf-8")
            (ignored / "skip.py").write_text("def skip():\n    return 1\n", encoding="utf-8")

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(result.exit_code, 0, result.output)

            self.assertTrue((kept / "INDEX.lsdf").exists())
            self.assertFalse((ignored / "INDEX.lsdf").exists())

    def test_sync_check_detects_drift(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()

            py_file = pkg / "app.py"
            py_file.write_text("def run():\n    return 1\n", encoding="utf-8")

            # Generate initial indices
            gen_result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(gen_result.exit_code, 0, gen_result.output)

            up_to_date = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(up_to_date.exit_code, 0, up_to_date.output)
            self.assertIn("All indices are up to date", up_to_date.output)

            # Drift: change the source
            py_file.write_text("def run(name):\n    return name\n", encoding="utf-8")
            drift = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(drift.exit_code, 1, drift.output)
            self.assertIn("L-SDF drift detected", drift.output)

    def test_gen_writes_meta_json(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(result.exit_code, 0, result.output)

            meta_path = root / ".lsdf" / "meta.json"
            self.assertTrue(meta_path.exists())

            import json
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["generator"], "lsdf-core")
            self.assertIn("version", meta)
            self.assertIn("generated_at", meta)

            indices = meta["indices"]
            nav_key = str(Path("pkg") / "INDEX.lsdf")
            detail_key = str(Path("pkg") / "INDEX.detail.lsdf")
            self.assertIn(nav_key, indices)
            self.assertIn(detail_key, indices)

            nav_entry = indices[nav_key]
            self.assertEqual(nav_entry["profile"], "nav")
            self.assertIn("source_files", nav_entry)
            self.assertIn("source_hash", nav_entry)
            self.assertIn("index_hash", nav_entry)
            self.assertIn(str(Path("pkg") / "app.py"), nav_entry["source_files"])

    def test_sync_uses_meta_fast_path(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()
            py_file = pkg / "app.py"
            py_file.write_text("def run():\n    return 1\n", encoding="utf-8")

            self.runner.invoke(self.main, ["gen", str(root), "--recursive"])

            # Up to date — fast path should pass
            result = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("All indices are up to date", result.output)

            # Modify source — fast path detects staleness via source hash
            py_file.write_text("def run(name):\n    return name\n", encoding="utf-8")
            result = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("L-SDF drift detected", result.output)

    def test_sync_detects_manual_index_edit(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            self.runner.invoke(self.main, ["gen", str(root), "--recursive"])

            # Manually edit the index without changing source
            (pkg / "INDEX.lsdf").write_text("manually edited\n", encoding="utf-8")
            result = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("L-SDF drift detected", result.output)

    def test_trans_rejects_missing_and_unsupported_files(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            missing = self.runner.invoke(self.main, ["trans", str(root / "missing.md")])
            self.assertEqual(missing.exit_code, 1, missing.output)
            self.assertIn("File not found", missing.output)

            unsupported = root / "script.py"
            unsupported.write_text("print('hello')\n", encoding="utf-8")
            result = self.runner.invoke(self.main, ["trans", str(unsupported)])
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("Unsupported input type", result.output)

    def test_init_preserves_existing_agent_files(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                lsdf_dir = Path(".lsdf")
                lsdf_dir.mkdir()
                existing = lsdf_dir / "lsdf_instructions.md"
                existing.write_text("custom instructions\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(existing.read_text(encoding="utf-8"), "custom instructions\n")
                self.assertIn("preserved", result.output)

    def test_init_creates_lsdfignore_with_default_entries(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                ignore_text = Path(".lsdfignore").read_text(encoding="utf-8")
                self.assertIn(".pytest_cache\n", ignore_text)
                self.assertIn(".vscode\n", ignore_text)
                self.assertIn(".github\n", ignore_text)

    def test_init_builds_project_manifest_from_repo_structure(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("pyproject.toml").write_text(
                    "[project]\nname = 'demo'\ndependencies = ['fastapi', 'pydantic']\n",
                    encoding="utf-8",
                )
                Path("src").mkdir()
                Path("tests").mkdir()
                Path("docs").mkdir()
                Path(".github").mkdir()

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn(":", project_lsdf)
                self.assertIn("Python", project_lsdf)
                self.assertIn(" @src:main-code", project_lsdf)
                self.assertIn(" @tests:test-suite", project_lsdf)
                self.assertIn(" @docs:documentation", project_lsdf)
                self.assertNotIn(".github", project_lsdf)
                self.assertIn(" ~[FastAPI,Pydantic]", project_lsdf)

    def test_init_manifest_respects_lsdfignore_entries(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
                Path(".lsdfignore").write_text(".git\n__pycache__\n", encoding="utf-8")
                Path(".github").mkdir()

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn(" @.github:ci-cd", project_lsdf)

    def test_init_writes_lsdf_version_to_project_manifest(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn("$lsdf:", project_lsdf)

    def test_init_detects_version_upgrade_and_overwrites_templates(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                # Simulate an old project.lsdf with no $lsdf: line (pre-1.1)
                Path("project.lsdf").write_text("^myproject:Python\n", encoding="utf-8")
                Path(".lsdf").mkdir()
                old_instructions = Path(".lsdf") / "lsdf_instructions.md"
                old_instructions.write_text("old instructions\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                self.assertIn("Upgrading", result.output)
                # Template file must be overwritten with current version content
                self.assertNotEqual(
                    old_instructions.read_text(encoding="utf-8"), "old instructions\n"
                )
                # project.lsdf must now carry the current version
                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn("$lsdf:", project_lsdf)

    def test_init_updates_agent_config_instructions_on_upgrade(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                # Simulate old project: content before, L-SDF section, content after
                Path("project.lsdf").write_text("^myproject:Python\n", encoding="utf-8")
                Path("CLAUDE.md").write_text(
                    "# My Project\n\n## L-SDF Protocol\nold instructions\n\n# Other Section\nkept\n",
                    encoding="utf-8",
                )

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Updated", result.output)

                claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
                # Old instructions replaced
                self.assertNotIn("old instructions", claude_md)
                # L-SDF Protocol heading present
                self.assertIn("L-SDF Protocol", claude_md)
                # Content before the sentinel preserved
                self.assertIn("# My Project", claude_md)
                # Content after the sentinel preserved
                self.assertIn("# Other Section", claude_md)
                self.assertIn("kept", claude_md)
                # Sentinel appears exactly once
                self.assertEqual(claude_md.count("L-SDF Protocol"), 1)

    def test_init_warns_when_project_version_is_newer_than_cli(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                # Simulate a project.lsdf from a future version
                Path("project.lsdf").write_text("^myproject:Python\n$lsdf:99.0.0\n", encoding="utf-8")
                Path(".lsdf").mkdir()
                old_content = "future instructions\n"
                (Path(".lsdf") / "lsdf_instructions.md").write_text(old_content, encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                self.assertIn("newer version", result.output)
                self.assertIn("99.0.0", result.output)
                # Templates must NOT be overwritten
                self.assertEqual(
                    (Path(".lsdf") / "lsdf_instructions.md").read_text(encoding="utf-8"),
                    old_content,
                )

    def test_init_skips_templates_when_version_matches(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                # First init
                self.runner.invoke(self.main, ["init"])
                # Simulate a user customization to lsdf_instructions.md
                custom = Path(".lsdf") / "lsdf_instructions.md"
                custom.write_text("my custom instructions\n", encoding="utf-8")

                # Re-run init — same version, so templates must NOT be overwritten
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertNotIn("Upgrading", result.output)
                self.assertEqual(custom.read_text(encoding="utf-8"), "my custom instructions\n")

    def test_init_refreshes_existing_project_manifest(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("project.lsdf").write_text("^old:Python\n", encoding="utf-8")
                Path("package.json").write_text('{"dependencies":{"react":"1.0.0"}}\n', encoding="utf-8")
                Path("web").mkdir()

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertNotIn("^old:Python", project_lsdf)
                self.assertIn("Node", project_lsdf)
                self.assertIn(" @web:web-client", project_lsdf)
                self.assertIn(" ~[React]", project_lsdf)

    def test_init_uses_environment_yml_as_optional_dependency_hint(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("environment.yml").write_text(
                    "name: demo\n"
                    "dependencies:\n"
                    "  - python=3.11\n"
                    "  - pip\n"
                    "  - pip:\n"
                    "    - fastapi\n"
                    "    - sqlalchemy\n",
                    encoding="utf-8",
                )

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn("Python", project_lsdf)
                self.assertIn(" ~[FastAPI,SQLAlchemy]", project_lsdf)

    def test_init_uses_dockerfile_as_optional_framework_hint(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("Dockerfile").write_text(
                    "FROM python:3.11-slim\n"
                    'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]\n',
                    encoding="utf-8",
                )
                Path("app").mkdir()

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn(" @app:application", project_lsdf)
                self.assertIn(" ~[FastAPI]", project_lsdf)

    def test_gen_writes_meta_at_project_root_not_subdir(self):
        """meta.json must land at the project root even when gen is invoked on a subdirectory."""
        import json

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Simulate a project root by placing project.lsdf there
            (root / "project.lsdf").write_text("^myproject:Python\n", encoding="utf-8")
            src = root / "src"
            src.mkdir()
            (src / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            # Invoke gen on the subdirectory, not the root
            result = self.runner.invoke(self.main, ["gen", str(src)])
            self.assertEqual(result.exit_code, 0, result.output)

            # meta.json must be at the project root, not in src/
            meta_at_root = root / ".lsdf" / "meta.json"
            meta_at_src = src / ".lsdf" / "meta.json"
            self.assertTrue(meta_at_root.exists(), "meta.json should be at project root")
            self.assertFalse(meta_at_src.exists(), "meta.json must NOT be in the scan subdirectory")

            meta = json.loads(meta_at_root.read_text(encoding="utf-8"))
            # Keys should be relative to project root, e.g. "src/INDEX.lsdf"
            indices = meta["indices"]
            expected_key = str(Path("src") / "INDEX.lsdf")
            self.assertIn(expected_key, indices)

if __name__ == '__main__':
    unittest.main()
