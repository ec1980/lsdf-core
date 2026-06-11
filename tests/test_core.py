import unittest
from unittest.mock import patch
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

    def test_from_markdown_compacts_function_signatures_and_calls(self):
        md = (
            "## File: cli.py\n"
            " - **Function:** build_output_path(output_dir: Path, user_id: str, generated_at): Path\n"
            " - **Function:** build_parser: argparse.ArgumentParser\n"
            " - **Function:** write_output(path: Path, payload: dict)\n"
            " - **Function:** main(argv: Optional[Sequence[str]]): int\n"
            "   - *Calls:* `build_parser`, `build_output_path`, `write_output`"
        )
        lsdf = from_markdown(md)
        self.assertIn("@cli.py", lsdf)
        self.assertIn(" !build_output_path(output_dir:Path,user_id:s,generated_at):Path", lsdf)
        self.assertIn(" !build_parser:argparse.ArgumentParser", lsdf)
        self.assertIn(" !write_output(path:Path,payload:dict)", lsdf)
        self.assertIn("@cli.py > build_parser,build_output_path,write_output", lsdf)
        self.assertIn(" !main(argv:q[s]?):i", lsdf)

    def test_from_markdown_emphasis_and_code_blocks(self):
        md = "**Dependencies:** requests, click\n```python\nprint('hi')\n```"
        lsdf = from_markdown(md)
        self.assertIn("~requests,click", lsdf)
        self.assertIn("\\print('hi')", lsdf)

    def test_from_markdown_accepts_imports_label(self):
        md = (
            "## File: cli.py\n"
            " - **Imports:** `argparse`, `json`\n"
            " - **Imports:** `deal_scorer.pipeline`: `run_watch_pipeline`, `run_watches_pipeline`\n"
            " - **Imports:** `pathlib`: `Path`\n"
            " - **Imports:** `pydantic`: `ValidationError`\n"
            " - **Imports:** `typing`: `Sequence`"
        )
        lsdf = from_markdown(md)
        self.assertIn("@cli.py", lsdf)
        self.assertIn(" ~argparse,json", lsdf)
        self.assertIn(" ~deal_scorer.pipeline:run_watch_pipeline,run_watches_pipeline", lsdf)
        self.assertIn(" ~pathlib:Path", lsdf)
        self.assertIn(" ~pydantic:ValidationError", lsdf)
        self.assertIn(" ~typing:Sequence", lsdf)

    def test_from_markdown_compacts_schema_field_bullets(self):
        md = (
            "## File: cli.py\n"
            " - **Schema:** RawVtgDealRow\n"
            "   - deal_id: str\n"
            "   - deal_url: Optional[str]\n"
            "   - nights: Optional[str]\n"
            "   - depart_date: Optional[str]\n"
            "   - departs_from: Optional[str]\n"
            "   - departs_from_url: Optional[str]"
        )
        lsdf = from_markdown(md)
        self.assertIn("@cli.py", lsdf)
        self.assertIn(" ?RawVtgDealRow", lsdf)
        self.assertIn(" ?deal_id:s", lsdf)
        self.assertIn(" ?deal_url:s?", lsdf)
        self.assertIn(" ?nights:s?", lsdf)
        self.assertIn(" ?depart_date:s?", lsdf)
        self.assertIn(" ?departs_from:s?", lsdf)
        self.assertIn(" ?departs_from_url:s?", lsdf)

    def test_from_markdown_collapses_short_schema_blocks_inline(self):
        md = (
            "## File: contracts.py\n"
            "  - **Schema:** UserStatus\n"
            "    - active: bool"
        )
        lsdf = from_markdown(md)
        self.assertIn("@contracts.py", lsdf)
        self.assertIn(" ?UserStatus{active:b}", lsdf)
        self.assertNotIn(" ?UserStatus\n  ?active:b", lsdf)

    def test_from_markdown_keeps_long_schema_blocks_multiline(self):
        md = (
            "## File: contracts.py\n"
            "  - **Schema:** RawVtgDealRow\n"
            "    - deal_id: str\n"
            "    - deal_url: Optional[str]\n"
            "    - nights: Optional[str]\n"
            "    - depart_date: Optional[str]\n"
            "    - departs_from: Optional[str]\n"
            "    - departs_from_url: Optional[str]"
        )
        lsdf = from_markdown(md)
        self.assertIn(" ?RawVtgDealRow", lsdf)
        self.assertIn("  ?deal_id:s", lsdf)
        self.assertNotIn("?RawVtgDealRow{", lsdf)

    def test_from_markdown_compacts_entity_field_bullets(self):
        md = (
            "## Class: MatchedFeedbackReason\n"
            "  - canonical_reason: str\n"
            "  - matched_alias: str\n"
            "  - original_reason: str\n"
            "  - deal_id: str\n"
            "  - vote: int\n"
            "  - similarity: float"
        )
        lsdf = from_markdown(md)
        self.assertIn("@MatchedFeedbackReason", lsdf)
        self.assertIn(" ?canonical_reason:s", lsdf)
        self.assertIn(" ?matched_alias:s", lsdf)
        self.assertIn(" ?original_reason:s", lsdf)
        self.assertIn(" ?deal_id:s", lsdf)
        self.assertIn(" ?vote:i", lsdf)
        self.assertIn(" ?similarity:f", lsdf)

    def test_from_markdown_uses_parent_relative_indent_for_schema_fields(self):
        md = (
            "## File: contracts.py\n"
            "  - **Schema:** RawVtgDealRow\n"
            "      - deal_id: str\n"
            "      - deal_url: Optional[str]"
        )
        lsdf = from_markdown(md)
        self.assertIn("@contracts.py", lsdf)
        self.assertIn(" ?RawVtgDealRow", lsdf)
        self.assertTrue(
            "  ?deal_id:s" in lsdf or " ?RawVtgDealRow{deal_id:s,deal_url:s?}" in lsdf
        )
        self.assertTrue(
            "  ?deal_url:s?" in lsdf or " ?RawVtgDealRow{deal_id:s,deal_url:s?}" in lsdf
        )
        self.assertNotIn("   ?deal_id:s", lsdf)

    def test_from_markdown_compacts_function_signature_with_nested_generics(self):
        md = (
            "## File: update_watch.py\n"
            "  - **Function:** build_compact_scored_watch_for_feedback("
            "current_scored_watch: dict[str, Any], feedback_for_watch: dict[str, Any], watch: WatchFile"
            "): dict[str, Any]"
        )
        lsdf = from_markdown(md)
        self.assertIn("@update_watch.py", lsdf)
        self.assertIn(
            " !build_compact_scored_watch_for_feedback(current_scored_watch:{s:a},feedback_for_watch:{s:a},watch:WatchFile):{s:a}",
            lsdf,
        )

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

    def test_expand_signature(self):
        from src.core import _expand_signature
        self.assertEqual(_expand_signature('run'), 'run')
        self.assertEqual(_expand_signature('parse_float(value:s?):f?'),
                         'parse_float(value: Optional[str]): Optional[float]')
        self.assertEqual(_expand_signature('greet(names:[s]):[s]'),
                         'greet(names: list[str]): list[str]')
        self.assertEqual(_expand_signature('score(deal:Deal,cfg:Cfg):DealScore'),
                         'score(deal: Deal, cfg: Cfg): DealScore')
        self.assertEqual(_expand_signature('run > Greeter.greet'), 'run > Greeter.greet')

    def test_to_markdown_call_edges(self):
        md = to_markdown("!run > Greeter.greet,parse")
        self.assertIn("### Function: run", md)
        self.assertIn("*Calls:*", md)
        self.assertIn("`Greeter.greet`", md)
        self.assertIn("`parse`", md)

    def test_to_markdown_call_edges_nested(self):
        md = to_markdown(" !greet(names:[s]):[s] > say_hello")
        self.assertIn("- **Function:** greet(names: list[str]): list[str]", md)
        self.assertIn("*Calls:*", md)
        self.assertIn("`say_hello`", md)

    def test_to_markdown_inline_schema(self):
        md = to_markdown("?User{id:uuid,email:s,active:b}")
        self.assertIn("#### Schema: User", md)
        self.assertIn("  - id: uuid", md)
        self.assertIn("  - email: str", md)
        self.assertIn("  - active: bool", md)

    def test_to_markdown_inline_schema_nested(self):
        md = to_markdown(" ?Token{value:s,expires:i}")
        self.assertIn("- **Schema:** Token", md)
        self.assertIn("value: str", md)

    def test_to_markdown_schema_field_lines(self):
        md = to_markdown("?User\n ?id:uuid\n ?email:s")
        self.assertIn("#### Schema: User", md)
        self.assertIn("  - id: uuid", md)
        self.assertIn("  - email: str", md)

    def test_expand_type_aliases(self):
        from src.core import _expand_type
        self.assertEqual(_expand_type('s'), 'str')
        self.assertEqual(_expand_type('i'), 'int')
        self.assertEqual(_expand_type('f'), 'float')
        self.assertEqual(_expand_type('b'), 'bool')
        self.assertEqual(_expand_type('a'), 'Any')
        self.assertEqual(_expand_type('[s]'), 'list[str]')
        self.assertEqual(_expand_type('q[s]'), 'Sequence[str]')
        self.assertEqual(_expand_type("l['a','b']"), "Literal['a','b']")
        self.assertEqual(_expand_type('{s:i}'), 'dict[str, int]')
        self.assertEqual(_expand_type('b?'), 'Optional[bool]')
        self.assertEqual(_expand_type('[s]?'), 'Optional[list[str]]')
        self.assertEqual(_expand_type('{s:s}?'), 'Optional[dict[str, str]]')
        self.assertEqual(_expand_type('date?'), 'Optional[date]')
        self.assertEqual(_expand_type('date'), 'date')

    def test_to_markdown_schema_field_expanded_types(self):
        lsdf = (
            "?DealDerived\n"
            " ?departure_date:date?\n"
            " ?is_roundtrip:b?\n"
            " ?available_cabin_classes:[s]\n"
            " ?selected_offer:{s:s}?\n"
            " ?display_price_now:f?\n"
        )
        md = to_markdown(lsdf)
        self.assertIn("#### Schema: DealDerived", md)
        self.assertIn("departure_date: Optional[date]", md)
        self.assertIn("is_roundtrip: Optional[bool]", md)
        self.assertIn("available_cabin_classes: list[str]", md)
        self.assertIn("selected_offer: Optional[dict[str, str]]", md)
        self.assertIn("display_price_now: Optional[float]", md)

    def test_to_markdown_expands_new_short_types(self):
        lsdf = (
            "?TypeDemo\n"
            " ?payload:a\n"
            " ?created_at:datetime\n"
            " ?source_path:Path\n"
            " ?levels:q[i]\n"
            " ?status:l['new','done']"
        )
        md = to_markdown(lsdf)
        self.assertIn("payload: Any", md)
        self.assertIn("created_at: datetime", md)
        self.assertIn("source_path: Path", md)
        self.assertIn("levels: Sequence[int]", md)
        self.assertIn("status: Literal['new','done']", md)

    def test_to_markdown_imports_with_symbols(self):
        md = to_markdown("~pydantic:BaseModel,Field")
        self.assertIn("`pydantic`", md)
        self.assertIn("`BaseModel`", md)
        self.assertIn("`Field`", md)

    def test_to_markdown_imports_framework_list(self):
        md = to_markdown("~[FastAPI,Pydantic]")
        self.assertIn("`FastAPI`", md)
        self.assertIn("`Pydantic`", md)

    def test_to_markdown_imports_bare_modules(self):
        md = to_markdown("~os,pathlib")
        self.assertIn("`os`", md)
        self.assertIn("`pathlib`", md)

    def test_to_markdown_route(self):
        md = to_markdown(" #GET /users")
        self.assertIn("**Route:** `GET /users`", md)

    def test_to_markdown_entry_point(self):
        md = to_markdown(" !lsdf=src.cli:main")
        self.assertIn("**Entry point:**", md)
        self.assertIn("`lsdf`", md)
        self.assertIn("`src.cli:main`", md)

    def test_to_markdown_lsdf_version_annotation(self):
        md = to_markdown("$lsdf:1.1.0")
        self.assertIn("lsdf-core 1.1.0", md)

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

            self.assertIn("@sample.py", nav)
            self.assertIn("@sample.py", detail)
            self.assertNotIn("~[", nav)
            self.assertNotIn("~[", detail)

            # Nav: reduced module-level import view
            self.assertIn(" ~os,os.path,package.module", nav)
            self.assertNotIn(" ~package.module:Thing,helper", nav)

            # Nav: schema classes must NOT appear
            self.assertNotIn("?FeatureSpec", nav)
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
            self.assertIn(" ~os,os.path", detail)
            self.assertIn(" ~package.module:Thing,helper", detail)
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

            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertIn(" ~deal_scorer.cli", nav)
            self.assertIn(" ~deal_scorer.cli:main", detail)
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

    def test_python_generator_extracts_leading_single_line_comments_into_detail(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "# Top-level note for run\n"
                "def run():\n"
                "    return 1\n"
                "\n"
                "class Greeter:\n"
                '    """Greeter class doc."""\n'
                "    # Field note\n"
                "    name: str\n"
                "    # Method note\n"
                "    def greet(self):\n"
                '        """Method doc."""\n'
                "        return self.name\n",
                encoding="utf-8",
            )

            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertIn(" !run", nav)
            self.assertNotIn("$Top-level note for run", nav)

            self.assertIn(" $Top-level note for run", detail)
            self.assertIn(" $Greeter class doc.", detail)
            self.assertIn("  $Field note", detail)
            self.assertIn("  $Method note", detail)
            self.assertIn("  $Method doc.", detail)
            self.assertIn(" !run", detail)
            self.assertIn(" @Greeter", detail)

    def test_python_generator_omits_overlong_annotations(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            long_comment = "A" * 81
            long_doc = "B" * 81
            file_path.write_text(
                f"# {long_comment}\n"
                "def run():\n"
                f'    """{long_doc}"""\n'
                "    return 1\n",
                encoding="utf-8",
            )

            _, detail = PythonGenerator().generate(str(file_path))
            self.assertNotIn(long_comment, detail)
            self.assertNotIn(long_doc, detail)
            self.assertIn(" !run", detail)

    def test_python_generator_type_aliases(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from pathlib import Path\n"
                "from typing import Any, Literal, Optional, Sequence\n"
                "from datetime import date, datetime\n"
                "\n"
                "def process(name: str, count: int, active: bool) -> float:\n"
                "    return 1.0\n"
                "\n"
                "def load(items: list[str]) -> dict[str, int]:\n"
                "    return {}\n"
                "\n"
                "def maybe(val: Optional[str]) -> str | None:\n"
                "    return val\n"
                "\n"
                "def enrich(payload: Any, created_at: datetime, due: date, path: Path, labels: Sequence[str]) -> Literal['ok', 'bad']:\n"
                "    return 'ok'\n",
                encoding="utf-8",
            )

            _, detail = PythonGenerator().generate(str(file_path))
            self.assertIn("!process(name:s,count:i,active:b):f", detail)
            self.assertIn("!load(items:[s]):{s:i}", detail)
            self.assertIn("!maybe(val:s?)", detail)
            self.assertIn(":s?", detail)
            self.assertIn("!enrich(payload:a,created_at:datetime,due:date,path:Path,labels:q[s]):l['ok','bad']", detail)

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

            # Schema classes must NOT appear in nav
            self.assertNotIn("?User", nav)
            self.assertNotIn("?Point", nav)
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

    def test_python_generator_skips_init_file(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "__init__.py"
            file_path.write_text("from .core import run\n", encoding="utf-8")
            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertIsNone(nav)
            self.assertIsNone(detail)

    def test_python_generator_skips_future_imports(self):
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(
                "from __future__ import annotations\nimport __future__\nimport os\ndef run(): pass\n",
                encoding="utf-8",
            )
            nav, detail = PythonGenerator().generate(str(file_path))
            self.assertNotIn("__future__", nav)
            self.assertNotIn("__future__", detail)
            self.assertIn("~os", nav)

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
        from src.cli import main, _package_version

        self.runner = CliRunner()
        self.main = main
        self.package_version = _package_version()

    def _write_project_lsdf(self, root: Path, version: str | None = None):
        version = version or self.package_version
        root.joinpath("project.lsdf").write_text(f"^test:Python\n$lsdf:{version}\n", encoding="utf-8")

    def test_gen_produces_both_index_tiers(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_project_lsdf(root)
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
            self._write_project_lsdf(root)
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
            self.assertIn(f"Updated: {src / 'INDEX.lsdf'}", rewritten.output)
            self.assertNotEqual((src / "INDEX.lsdf").read_text(encoding="utf-8"), "manual edit\n")

    def test_gen_sorts_files_alphabetically(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_project_lsdf(root)
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
            self._write_project_lsdf(root)
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
            self._write_project_lsdf(root)
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

    def test_clean_removes_generated_indices_and_meta(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_project_lsdf(root)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertTrue((pkg / "INDEX.lsdf").exists())
            self.assertTrue((pkg / "INDEX.detail.lsdf").exists())
            self.assertTrue((root / ".lsdf" / "meta.json").exists())

            result = self.runner.invoke(self.main, ["clean", str(root), "--recursive", "--yes"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn(f"Deleted {pkg / 'INDEX.lsdf'}", result.output)
            self.assertIn(f"Deleted {pkg / 'INDEX.detail.lsdf'}", result.output)
            self.assertIn(f"Deleted {root / '.lsdf' / 'meta.json'}", result.output)
            self.assertFalse((pkg / "INDEX.lsdf").exists())
            self.assertFalse((pkg / "INDEX.detail.lsdf").exists())
            self.assertFalse((root / ".lsdf" / "meta.json").exists())

    def test_clean_all_removes_bootstrap_files_and_managed_agent_block(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("CLAUDE.md").write_text("# Project\n", encoding="utf-8")
                init_result = self.runner.invoke(self.main, ["init", "--ci"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                pkg = Path("pkg")
                pkg.mkdir()
                (pkg / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
                gen_result = self.runner.invoke(self.main, ["gen", ".", "--recursive"])
                self.assertEqual(gen_result.exit_code, 0, gen_result.output)

                result = self.runner.invoke(self.main, ["clean", ".", "--recursive", "--all", "--yes"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn(".lsdf", result.output)
                self.assertIn(".lsdfignore", result.output)
                self.assertIn("project.lsdf", result.output)
                self.assertIn("CLAUDE.md", result.output)

                self.assertFalse(Path("pkg/INDEX.lsdf").exists())
                self.assertFalse(Path("pkg/INDEX.detail.lsdf").exists())
                self.assertFalse(Path("project.lsdf").exists())
                self.assertFalse(Path(".lsdf").exists())
                self.assertFalse(Path(".lsdfignore").exists())

                claude_text = Path("CLAUDE.md").read_text(encoding="utf-8")
                self.assertIn("# Project", claude_text)
                self.assertNotIn("LSDF:START", claude_text)
                self.assertNotIn("LSDF:END", claude_text)

    def test_gen_writes_meta_json(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_project_lsdf(root)
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
            self._write_project_lsdf(root)
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
            self._write_project_lsdf(root)
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

    def test_commands_warn_when_project_manifest_is_missing(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            result = self.runner.invoke(self.main, ["gen", str(root), "--recursive"])
            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("Run `lsdf init` first", result.output)
            self.assertFalse((pkg / "INDEX.lsdf").exists())
            self.assertFalse((pkg / "INDEX.detail.lsdf").exists())

    def test_commands_warn_when_project_manifest_version_differs(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "project.lsdf").write_text("^demo:Python\n$lsdf:9.9.9\n", encoding="utf-8")
            (root / "module.lsdf").write_text("@module.py\n", encoding="utf-8")

            commands = [
                ["clean", str(root), "--yes"],
                ["sync", str(root)],
                ["stats", str(root)],
                ["trans", str(root / "module.lsdf")],
            ]

            for argv in commands:
                result = self.runner.invoke(self.main, argv)
                self.assertNotEqual(result.exit_code, 0, result.output)
                self.assertIn("Run `lsdf init` to install or upgrade L-SDF metadata first.", result.output)

    def test_init_preserves_existing_agent_files(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                lsdf_dir = Path(".lsdf")
                lsdf_dir.mkdir()
                existing = lsdf_dir / "lsdf_instructions.md"
                existing.write_text("custom instructions\n", encoding="utf-8")
                Path("CLAUDE.md").write_text("# Project\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(existing.read_text(encoding="utf-8"), "custom instructions\n")
                self.assertNotIn("Created .lsdf/lsdf_instructions.md", result.output)
                self.assertIn("Appended file from .lsdf/lsdf_instructions.md to CLAUDE.md", result.output)
                self.assertIn("custom instructions", Path("CLAUDE.md").read_text(encoding="utf-8"))

    def test_init_creates_lsdfignore_with_default_entries(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Created .lsdfignore", result.output)
                self.assertIn("Created project.lsdf", result.output)

                ignore_text = Path(".lsdfignore").read_text(encoding="utf-8")
                self.assertIn(".lsdf/\n", ignore_text)
                self.assertIn(".pytest_cache\n", ignore_text)
                self.assertIn(".vscode\n", ignore_text)
                self.assertIn(".github\n", ignore_text)

    def test_init_adds_lsdf_dir_to_existing_lsdfignore(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path(".lsdfignore").write_text(".git\n__pycache__\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Appended .lsdf/ to .lsdfignore", result.output)

                ignore_text = Path(".lsdfignore").read_text(encoding="utf-8")
                self.assertIn(".lsdf/\n", ignore_text)
                self.assertIn(".git\n", ignore_text)

    def test_init_creates_gitignore_with_meta_json_entry(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Created .gitignore with .lsdf/meta.json", result.output)

                ignore_text = Path(".gitignore").read_text(encoding="utf-8")
                self.assertIn(".lsdf/meta.json\n", ignore_text)

    def test_init_appends_meta_json_to_existing_gitignore(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path(".gitignore").write_text("__pycache__/\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Appended .lsdf/meta.json to .gitignore", result.output)

                ignore_text = Path(".gitignore").read_text(encoding="utf-8")
                self.assertIn("__pycache__/\n", ignore_text)
                self.assertIn(".lsdf/meta.json\n", ignore_text)

    def test_init_does_not_duplicate_meta_json_in_gitignore(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path(".gitignore").write_text(".lsdf/meta.json\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertNotIn("gitignore", result.output.lower())

                ignore_text = Path(".gitignore").read_text(encoding="utf-8")
                self.assertEqual(ignore_text.count(".lsdf/meta.json\n"), 1)

    def test_init_does_not_duplicate_lsdf_dir_in_lsdfignore(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path(".lsdfignore").write_text(".lsdf/\n.git\n", encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                ignore_text = Path(".lsdfignore").read_text(encoding="utf-8")
                self.assertEqual(ignore_text.count(".lsdf/\n"), 1)

    def test_init_includes_entry_points_in_manifest(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path("pyproject.toml").write_text(
                    "[project]\nname = 'demo'\n\n"
                    "[project.scripts]\n"
                    'demo = "src.cli:main"\n'
                    'demo-worker = "src.worker:run"\n',
                    encoding="utf-8",
                )

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn(" !demo=src.cli:main", project_lsdf)
                self.assertIn(" !demo-worker=src.worker:run", project_lsdf)

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

                with patch("src.cli._package_version", return_value="1.1.0"):
                    result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                self.assertIn("Upgrading", result.output)
                self.assertIn("Updated .lsdf/lsdf_instructions.md", result.output)
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

                with patch("src.cli._package_version", return_value="1.1.0"):
                    result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Updated", result.output)

                claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
                # Old instructions replaced
                self.assertNotIn("old instructions", claude_md)
                self.assertIn("<!-- LSDF:START -->", claude_md)
                self.assertIn("<!-- LSDF:END -->", claude_md)
                # L-SDF Protocol heading present
                self.assertIn("L-SDF Protocol", claude_md)
                # Content before the sentinel preserved
                self.assertIn("# My Project", claude_md)
                # Content after the sentinel preserved
                self.assertIn("# Other Section", claude_md)
                self.assertIn("kept", claude_md)
                # Sentinel appears exactly once
                self.assertEqual(claude_md.count("L-SDF Protocol"), 1)

    def test_init_refreshes_agent_instructions_when_project_manifest_is_missing(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                Path(".lsdf").mkdir()
                Path(".lsdf/lsdf_instructions.md").write_text(
                    "# L-SDF Protocol\nnew instructions\n",
                    encoding="utf-8",
                )
                Path("CLAUDE.md").write_text(
                    "# My Project\n\n## L-SDF Protocol\nold instructions\n\n# Other Section\nkept\n",
                    encoding="utf-8",
                )

                with patch("src.cli._package_version", return_value="1.1.2"):
                    result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Initializing L-SDF", result.output)
                self.assertIn(
                    "Updated L-SDF instructions from .lsdf/lsdf_instructions.md in CLAUDE.md",
                    result.output,
                )

                project_lsdf = Path("project.lsdf").read_text(encoding="utf-8")
                self.assertIn("$lsdf:", project_lsdf)

                claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
                self.assertNotIn("old instructions", claude_md)
                self.assertIn("<!-- LSDF:START -->", claude_md)
                self.assertIn("<!-- LSDF:END -->", claude_md)
                self.assertIn("L-SDF Protocol", claude_md)
                self.assertIn("# Other Section", claude_md)
                self.assertIn("kept", claude_md)

    def test_init_warns_when_project_version_is_newer_than_cli(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                # Simulate a project.lsdf from a future version
                old_manifest = "^myproject:Python\n$lsdf:99.0.0\n"
                Path("project.lsdf").write_text(old_manifest, encoding="utf-8")
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
                self.assertEqual(Path("project.lsdf").read_text(encoding="utf-8"), old_manifest)

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
                self.assertNotIn("Skipped", result.output)
                self.assertEqual(custom.read_text(encoding="utf-8"), "my custom instructions\n")

    def test_init_ci_renders_workflow_with_installed_version(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                with patch("src.cli._package_version", return_value="1.2.3"):
                    result = self.runner.invoke(self.main, ["init", "--ci"])

                self.assertEqual(result.exit_code, 0, result.output)
                workflow = Path(".github/workflows/update-lsdf.yml").read_text(encoding="utf-8")
                self.assertIn("python -m pip install lsdf-core==1.2.3", workflow)
                self.assertNotIn("{{ LSDF_CORE_VERSION }}", workflow)

    def test_init_does_not_rewrite_project_manifest_when_version_matches(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                import src.cli as cli_module

                current_version = cli_module._package_version()
                original_manifest = "^custom:Python\n$lsdf:" + current_version + "\n"
                Path("project.lsdf").write_text(original_manifest, encoding="utf-8")

                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertNotIn("Updated project.lsdf", result.output)
                self.assertEqual(
                    Path("project.lsdf").read_text(encoding="utf-8"),
                    original_manifest,
                )

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

    def test_init_templates_dir_is_accessible_at_runtime(self):
        import src.cli as cli_module
        templates = Path(cli_module.__file__).parent / "_templates"
        self.assertTrue(templates.is_dir(), "_templates/ must exist alongside cli.py")
        for name in ("lsdf_spec.md", "update-lsdf.yml", "lsdf_instructions.md"):
            self.assertTrue((templates / name).exists(), f"_templates/{name} is missing")

    def test_init_copies_templates_without_warning(self):
        with TemporaryDirectory() as tmpdir:
            with self.runner.isolated_filesystem(temp_dir=tmpdir):
                result = self.runner.invoke(self.main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertNotIn("Template source not found", result.output)
                self.assertTrue(Path(".lsdf/lsdf_spec.md").exists())
                self.assertTrue(Path(".lsdf/lsdf_instructions.md").exists())

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
