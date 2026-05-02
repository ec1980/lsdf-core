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

    def test_python_generator_preserves_module_and_nested_hierarchy(self):
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
                "        def build_message(target):\n"
                "            return f'Hello {target}'\n"
                "        return build_message(name)\n"
                "\n"
                "def run_loop(user=None):\n"
                "    return user\n",
                encoding="utf-8",
            )

            output = PythonGenerator().generate(str(file_path))
            self.assertIn("@sample.py", output)
            self.assertIn(" ~[os, os.path, package.module.{Thing, helper}]", output)
            self.assertIn(" @FeatureSpec(BaseModel)", output)
            self.assertIn("  ?feature_id:str", output)
            self.assertIn("  ?enabled:bool", output)
            self.assertIn(" @Greeter", output)
            self.assertIn("  @Formatter", output)
            self.assertIn("   !format_name(self, name):str", output)
            self.assertIn("  !say_hello(self, name):str", output)
            self.assertIn("   !build_message(target)", output)
            self.assertIn(" !run_loop(user)", output)

    def test_python_generator_omits_none_return_annotation(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "def test_cli_scores_all_active_watches_from_watches_dir(tmp_path) -> None:\n"
                "    return None\n",
                encoding="utf-8",
            )

            output = PythonGenerator().generate(str(file_path))
            self.assertIn("!test_cli_scores_all_active_watches_from_watches_dir(tmp_path)", output)
            self.assertNotIn(":None", output)

    def test_python_generator_keeps_single_from_import_without_braces(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from deal_scorer.cli import main\n",
                encoding="utf-8",
            )

            output = PythonGenerator().generate(str(file_path))
            self.assertIn(" ~[deal_scorer.cli.main]", output)
            self.assertNotIn("{main}", output)

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

            output = PythonGenerator().generate(str(file_path))
            self.assertIn(" !health_check()", output)
            self.assertIn("  #GET /health", output)
            self.assertIn(" !create_item(item)", output)
            self.assertIn("  #POST /items", output)

    def test_python_generator_extracts_single_line_comments_only_when_enabled(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "# TODO handle legacy fallback\n"
                "# plain comment\n"
                "def run():\n"
                "    return 1\n",
                encoding="utf-8",
            )

            disabled_output = PythonGenerator().generate(str(file_path))
            enabled_output = PythonGenerator().generate(str(file_path), include_comments=True)

            self.assertNotIn("$TODO handle legacy fallback", disabled_output)
            self.assertIn(" $TODO handle legacy fallback", enabled_output)
            self.assertIn(" $plain comment", enabled_output)


class TestCLI(unittest.TestCase):
    def setUp(self):
        from click.testing import CliRunner
        from src.cli import main

        self.runner = CliRunner()
        self.main = main

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
            generated = (src / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertIn("@app.py", generated)
            self.assertIn(" !top()", generated)

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

            generated = (pkg / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertLess(generated.find("@alpha.py"), generated.find("@zeta.py"))

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

    def test_gen_extracts_comments_only_with_flag(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()

            (pkg / "app.py").write_text(
                "# TODO keep this note\n"
                "def run():\n"
                "    return 1\n",
                encoding="utf-8",
            )

            default_result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertEqual(default_result.exit_code, 0, default_result.output)
            default_index = (pkg / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertNotIn("$TODO keep this note", default_index)

            flagged_result = self.runner.invoke(
                self.main,
                ["gen", str(root), "--recursive", "--extract-comments"],
            )
            self.assertEqual(flagged_result.exit_code, 0, flagged_result.output)
            flagged_index = (pkg / "INDEX.lsdf").read_text(encoding="utf-8")
            self.assertIn(" $TODO keep this note", flagged_index)

    def test_sync_check_detects_drift(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()

            py_file = pkg / "app.py"
            index_file = pkg / "INDEX.lsdf"
            py_file.write_text("def run():\n    return 1\n", encoding="utf-8")
            index_file.write_text("@INDEX:pkg\n@app.py\n !run()\n", encoding="utf-8")

            up_to_date = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(up_to_date.exit_code, 0, up_to_date.output)
            self.assertIn("All indices are up to date", up_to_date.output)

            py_file.write_text("def run(name):\n    return name\n", encoding="utf-8")
            drift = self.runner.invoke(self.main, ["sync", str(root), "--check"])
            self.assertEqual(drift.exit_code, 1, drift.output)
            self.assertIn("L-SDF drift detected", drift.output)

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

if __name__ == '__main__':
    unittest.main()
