import ast
import os
import io
import tokenize


def _collapse_imports(direct_imports, from_imports):
    collapsed = []
    seen = set()

    for item in direct_imports:
        if item not in seen:
            seen.add(item)
            collapsed.append(item)

    for module_name in sorted(from_imports):
        symbols = []
        for symbol in from_imports[module_name]:
            if symbol not in symbols:
                symbols.append(symbol)
        if symbols == ["*"]:
            collapsed.append(f"{module_name}.*")
        elif len(symbols) == 1:
            collapsed.append(f"{module_name}.{symbols[0]}")
        else:
            collapsed.append(f"{module_name}.{{{', '.join(symbols)}}}")

    return collapsed

class PythonGenerator:
    def generate(self, file_path, include_comments=False):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
                node = ast.parse(source)
        except Exception:
            return None

        lsdf_lines = [f"@{os.path.basename(file_path)}"]

        # 1. Capture Imports
        direct_imports = []
        from_imports = {}
        for item in node.body:
            if isinstance(item, ast.Import):
                for n in item.names:
                    direct_imports.append(n.name)
            elif isinstance(item, ast.ImportFrom):
                if item.module:
                    for imported_name in item.names:
                        if imported_name.name == "*":
                            from_imports.setdefault(item.module, []).append("*")
                        else:
                            from_imports.setdefault(item.module, []).append(imported_name.name)

        if direct_imports or from_imports:
            ordered_imports = _collapse_imports(direct_imports, from_imports)
            lsdf_lines.append(f" ~[{', '.join(ordered_imports)}]")

        if include_comments:
            for comment in self._extract_single_line_comments(source):
                lsdf_lines.append(f" ${comment}")

        def get_ret(func_node):
            if func_node.returns:
                annotation = ast.unparse(func_node.returns)
                if annotation and annotation != "None":
                    return f":{annotation}"
            return ""

        def get_annotation(annotation_node):
            if annotation_node is None:
                return ""
            try:
                annotation = ast.unparse(annotation_node)
            except Exception:
                return ""
            return f":{annotation}" if annotation else ""

        def get_args(func_node):
            def format_arg(arg_node, prefix=""):
                return f"{prefix}{arg_node.arg}"

            positional = [format_arg(a) for a in func_node.args.posonlyargs + func_node.args.args]
            if func_node.args.vararg:
                positional.append(format_arg(func_node.args.vararg, "*"))
            positional.extend(format_arg(a) for a in func_node.args.kwonlyargs)
            if func_node.args.kwarg:
                positional.append(format_arg(func_node.args.kwarg, "**"))
            return positional

        def get_docstring(node):
            doc = ast.get_docstring(node)
            if not doc:
                return None
            # Collapse multi-line docstrings to their first non-empty line
            for line in doc.splitlines():
                line = line.strip()
                if line:
                    return line
            return None

        def get_routes(func_node):
            routes = []

            for decorator in func_node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue

                method_name = decorator.func.attr.lower()
                if method_name not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                    continue

                path_value = None
                if decorator.args:
                    first_arg = decorator.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        path_value = first_arg.value

                if path_value:
                    routes.append(f"#{method_name.upper()} {path_value}")

            return routes

        def append_node(item, indent=" "):
            if isinstance(item, ast.ClassDef):
                bases = []
                for base in item.bases:
                    try:
                        bases.append(ast.unparse(base))
                    except Exception:
                        continue
                suffix = f"({', '.join(bases)})" if bases else ""
                lsdf_lines.append(f"{indent}@{item.name}{suffix}")
                if include_comments:
                    doc = get_docstring(item)
                    if doc:
                        lsdf_lines.append(f"{indent} ${doc}")
                for sub in item.body:
                    if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                        annotation = get_annotation(sub.annotation)
                        lsdf_lines.append(f"{indent} ?{sub.target.id}{annotation}")
                    elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        append_node(sub, indent + " ")
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = get_args(item)
                ret = get_ret(item)
                lsdf_lines.append(f"{indent}!{item.name}({', '.join(args)}){ret}")
                if include_comments:
                    doc = get_docstring(item)
                    if doc:
                        lsdf_lines.append(f"{indent} ${doc}")
                for route in get_routes(item):
                    lsdf_lines.append(f"{indent} {route}")
                for sub in item.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        append_node(sub, indent + " ")

        # 2. Capture classes and functions in structural order
        for item in node.body:
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                append_node(item, " ")

        return "\n".join(lsdf_lines)

    _NOISE_PREFIXES = ("type:", "noqa", "pylint:", "mypy:", "fmt:", "isort:", "pyright:")

    def _extract_single_line_comments(self, source):
        comments = []

        try:
            tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        except Exception:
            return comments

        for token_type, token_string, _, _, line in tokens:
            if token_type != tokenize.COMMENT:
                continue

            # Skip inline comments (comment is not the first token on the line)
            if line.lstrip() and not line.lstrip().startswith("#"):
                continue

            content = token_string.lstrip("#").strip()
            if not content:
                continue

            # Skip linter/type-checker directives
            if any(content.startswith(p) for p in self._NOISE_PREFIXES):
                continue

            comments.append(content)

        return comments
