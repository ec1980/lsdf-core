import ast
import os


TYPE_ALIASES = {
    'str': 's', 'int': 'i', 'float': 'f', 'bool': 'b',
    'Any': 'a',
}


def _alias_annotation(node):
    """Recursively convert an AST annotation node to a compact alias string.
    Returns None when the type is None (signals caller to omit).
    """
    if node is None:
        return None

    if isinstance(node, ast.Constant):
        return None if node.value is None else str(node.value)

    if isinstance(node, ast.Name):
        if node.id == 'None':
            return None
        return TYPE_ALIASES.get(node.id, node.id)

    if isinstance(node, ast.Attribute):
        try:
            return ast.unparse(node)
        except Exception:
            return None

    if isinstance(node, ast.Subscript):
        value_name = node.value.id if isinstance(node.value, ast.Name) else None

        if value_name in ('list', 'List'):
            inner = _alias_annotation(node.slice)
            return f'[{inner}]' if inner else '[?]'

        if value_name in ('Sequence',):
            inner = _alias_annotation(node.slice)
            return f'q[{inner}]' if inner else 'q[?]'

        if value_name == 'Literal':
            if isinstance(node.slice, ast.Tuple):
                try:
                    literal_inner = ",".join(ast.unparse(elt) for elt in node.slice.elts)
                except Exception:
                    literal_inner = '?'
            else:
                try:
                    literal_inner = ast.unparse(node.slice)
                except Exception:
                    literal_inner = '?'
            return f'l[{literal_inner}]'

        if value_name in ('dict', 'Dict'):
            if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
                k = _alias_annotation(node.slice.elts[0]) or '?'
                v = _alias_annotation(node.slice.elts[1]) or '?'
                return f'{{{k}:{v}}}'
            return '{?:?}'

        if value_name == 'Optional':
            inner = _alias_annotation(node.slice)
            return f'{inner}?' if inner else '?'

        try:
            return ast.unparse(node)
        except Exception:
            return '?'

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # X | None  (Python 3.10+ union syntax)
        left = _alias_annotation(node.left)
        right = _alias_annotation(node.right)
        if right is None:
            return f'{left}?' if left else None
        if left is None:
            return f'{right}?' if right else None
        return f'{left}|{right}'

    try:
        return ast.unparse(node)
    except Exception:
        return None


def _emit_import_lines(direct_imports, from_imports, detail=False):
    """Return formatted ~-prefixed import lines for a file."""
    lines = []
    seen = set()
    direct = []
    for item in direct_imports:
        if item not in seen:
            seen.add(item)
            direct.append(item)

    if detail:
        if direct:
            lines.append(f" ~{','.join(direct)}")
        for module_name in sorted(from_imports):
            symbols = list(dict.fromkeys(from_imports[module_name]))
            if symbols == ['*']:
                lines.append(f" ~{module_name}.*")
            elif len(symbols) == 1:
                lines.append(f" ~{module_name}:{symbols[0]}")
            else:
                lines.append(f" ~{module_name}:{','.join(symbols)}")
        return lines

    nav_modules = []
    for item in direct:
        if item not in nav_modules:
            nav_modules.append(item)
    for module_name in sorted(from_imports):
        if module_name not in nav_modules:
            nav_modules.append(module_name)
    if nav_modules:
        lines.append(f" ~{','.join(nav_modules)}")
    return lines


SCHEMA_BASES = frozenset({
    'BaseModel', 'TypedDict', 'NamedTuple', 'Schema', 'Model',
    'SQLModel', 'DeclarativeBase', 'Base',
})

SCHEMA_LINE_BUDGET = 80
ANNOTATION_LINE_MAX = 80


def _is_schema_class(item):
    """Return True if the class should be emitted as a ? schema rather than an @ entity."""
    for dec in item.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == 'dataclass':
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == 'dataclass':
            return True
    for base in item.bases:
        name = base.id if isinstance(base, ast.Name) else (
            base.attr if isinstance(base, ast.Attribute) else None
        )
        if name in SCHEMA_BASES:
            return True
    return False


def _collect_callees(func_node, known_functions, known_classes, in_class=None):
    """Walk a function body and return project-level callees in order of first appearance."""
    callees = []
    seen = set()

    class _Visitor(ast.NodeVisitor):
        def visit_Call(self, node):
            callee = None
            func = node.func

            if isinstance(func, ast.Name):
                if func.id in known_functions:
                    callee = func.id

            elif isinstance(func, ast.Attribute):
                attr, value = func.attr, func.value
                if isinstance(value, ast.Name):
                    if value.id == 'self' and in_class:
                        if attr in known_classes.get(in_class, set()):
                            callee = attr
                    elif value.id in known_classes:
                        if attr in known_classes[value.id]:
                            callee = f'{value.id}.{attr}'
                elif isinstance(value, ast.Call):
                    # ClassName().method() instantiation pattern
                    inner = value.func
                    if isinstance(inner, ast.Name) and inner.id in known_classes:
                        if attr in known_classes[inner.id]:
                            callee = f'{inner.id}.{attr}'

            if callee and callee not in seen:
                callees.append(callee)
                seen.add(callee)
            self.generic_visit(node)

    _Visitor().visit(func_node)
    return callees


def _extract_leading_comments(source_lines, node):
    """Return contiguous single-line comments immediately above a node."""
    start_lineno = node.lineno
    decorators = getattr(node, "decorator_list", None) or []
    if decorators:
        start_lineno = min([start_lineno] + [dec.lineno for dec in decorators if hasattr(dec, "lineno")])

    comments = []
    i = start_lineno - 2  # convert to 0-based and move above the node
    while i >= 0:
        stripped = source_lines[i].strip()
        if not stripped:
            break
        if not stripped.startswith('#'):
            break
        if stripped.startswith('#!') or 'coding:' in stripped:
            i -= 1
            continue
        comment = stripped[1:].strip()
        if len(comment) <= ANNOTATION_LINE_MAX:
            comments.append(comment)
        i -= 1
    comments.reverse()
    return [comment for comment in comments if comment]


def _extract_short_docstring(node):
    """Return a compact first-line docstring annotation when useful."""
    doc = ast.get_docstring(node, clean=True)
    if not doc:
        return None
    first_line = doc.splitlines()[0].strip()
    if not first_line:
        return None
    if len(first_line) > ANNOTATION_LINE_MAX:
        return None
    return first_line


class PythonGenerator:
    def generate(self, file_path):
        """Parse a Python file and return (nav_content, detail_content).
        Returns (None, None) on parse error.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception:
            return None, None
        source_lines = source.splitlines()

        basename = os.path.basename(file_path)
        if basename == '__init__.py':
            return None, None

        # Registry for call edge detection
        known_functions = set()
        known_classes = {}
        for item in tree.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                known_functions.add(item.name)
            elif isinstance(item, ast.ClassDef):
                known_classes[item.name] = {
                    sub.name for sub in item.body
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                }

        # Imports
        direct_imports, from_imports = [], {}
        for item in tree.body:
            if isinstance(item, ast.Import):
                for n in item.names:
                    if n.name not in {'__future__', 'typing'}:
                        direct_imports.append(n.name)
            elif isinstance(item, ast.ImportFrom):
                if item.module and item.module not in {'__future__', 'typing'}:
                    for alias in item.names:
                        from_imports.setdefault(item.module, []).append(
                            '*' if alias.name == '*' else alias.name
                        )

        nav_import_lines = _emit_import_lines(direct_imports, from_imports, detail=False)
        detail_import_lines = _emit_import_lines(direct_imports, from_imports, detail=True)
        nav_lines = [f'@{basename}'] + nav_import_lines
        detail_lines = [f'@{basename}'] + detail_import_lines

        def _compact_args(func_node):
            args = []
            for arg in func_node.args.posonlyargs + func_node.args.args:
                if arg.arg in ('self', 'cls'):
                    continue
                alias = _alias_annotation(arg.annotation) if arg.annotation else None
                args.append(f'{arg.arg}:{alias}' if alias else arg.arg)
            if func_node.args.vararg:
                arg = func_node.args.vararg
                alias = _alias_annotation(arg.annotation) if arg.annotation else None
                args.append(f'*{arg.arg}:{alias}' if alias else f'*{arg.arg}')
            for arg in func_node.args.kwonlyargs:
                alias = _alias_annotation(arg.annotation) if arg.annotation else None
                args.append(f'{arg.arg}:{alias}' if alias else arg.arg)
            if func_node.args.kwarg:
                args.append(f'**{func_node.args.kwarg.arg}')
            return args

        def _compact_ret(func_node):
            if not func_node.returns:
                return ''
            alias = _alias_annotation(func_node.returns)
            return f':{alias}' if alias else ''

        def _get_routes(func_node):
            routes = []
            for dec in func_node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                method = dec.func.attr.lower()
                if method not in {'get', 'post', 'put', 'patch', 'delete', 'options', 'head'}:
                    continue
                if dec.args:
                    first = dec.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        routes.append(f'#{method.upper()} {first.value}')
            return routes

        def _should_skip(func_node):
            name = func_node.name
            # Dunder methods
            if name.startswith('__') and name.endswith('__'):
                return True
            # Single-underscore private helpers
            if name.startswith('_'):
                return True
            # Property accessors (@property, @x.setter, @x.deleter, @x.getter)
            for dec in func_node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == 'property':
                    return True
                if isinstance(dec, ast.Attribute) and dec.attr in ('setter', 'deleter', 'getter'):
                    return True
            # Test fixtures (@fixture / @pytest.fixture)
            for dec in func_node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == 'fixture':
                    return True
                if isinstance(dec, ast.Attribute) and dec.attr == 'fixture':
                    return True
            return False

        def _bases_suffix(item):
            bases = []
            for base in item.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    continue
            return f"({', '.join(bases)})" if bases else ''

        def append_nav(item, indent=' '):
            if isinstance(item, ast.ClassDef):
                if _is_schema_class(item):
                    return
                nav_lines.append(f'{indent}@{item.name}{_bases_suffix(item)}')
                for sub in item.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not _should_skip(sub):
                            append_nav(sub, indent + ' ')
                    elif isinstance(sub, ast.ClassDef):
                        append_nav(sub, indent + ' ')
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _should_skip(item):
                    return
                nav_lines.append(f'{indent}!{item.name}')

        def append_detail(item, indent=' ', in_class=None):
            if isinstance(item, ast.ClassDef):
                if _is_schema_class(item):
                    for comment in _extract_leading_comments(source_lines, item):
                        detail_lines.append(f'{indent}${comment}')
                    doc = _extract_short_docstring(item)
                    if doc:
                        detail_lines.append(f'{indent}${doc}')
                    fields = []
                    for sub in item.body:
                        if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                            ann = _alias_annotation(sub.annotation) if sub.annotation else None
                            fields.append(f'{sub.target.id}:{ann}' if ann else sub.target.id)
                    if not fields:
                        detail_lines.append(f'{indent}?{item.name}')
                    else:
                        one_line = f'{indent}?{item.name}{{{",".join(fields)}}}'
                        if len(one_line) <= SCHEMA_LINE_BUDGET:
                            detail_lines.append(one_line)
                        else:
                            detail_lines.append(f'{indent}?{item.name}')
                            for field in fields:
                                detail_lines.append(f'{indent} ?{field}')
                    return
                for comment in _extract_leading_comments(source_lines, item):
                    detail_lines.append(f'{indent}${comment}')
                doc = _extract_short_docstring(item)
                if doc:
                    detail_lines.append(f'{indent}${doc}')
                detail_lines.append(f'{indent}@{item.name}{_bases_suffix(item)}')
                for sub in item.body:
                    if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                        for comment in _extract_leading_comments(source_lines, sub):
                            detail_lines.append(f'{indent} ${comment}')
                        ann = _alias_annotation(sub.annotation) if sub.annotation else None
                        detail_lines.append(
                            f'{indent} ?{sub.target.id}:{ann}' if ann
                            else f'{indent} ?{sub.target.id}'
                        )
                    elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not _should_skip(sub):
                            append_detail(sub, indent + ' ', in_class=item.name)
                    elif isinstance(sub, ast.ClassDef):
                        append_detail(sub, indent + ' ', in_class=in_class)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _should_skip(item):
                    return
                for comment in _extract_leading_comments(source_lines, item):
                    detail_lines.append(f'{indent}${comment}')
                doc = _extract_short_docstring(item)
                if doc:
                    detail_lines.append(f'{indent}${doc}')
                args = _compact_args(item)
                ret = _compact_ret(item)
                arg_part = f"({','.join(args)})" if args else ''
                sig = f'{arg_part}{ret}'
                callees = _collect_callees(item, known_functions, known_classes, in_class=in_class)
                callee_str = f' > {",".join(callees)}' if callees else ''
                detail_lines.append(f'{indent}!{item.name}{sig}{callee_str}')
                for route in _get_routes(item):
                    detail_lines.append(f'{indent} {route}')

        for item in tree.body:
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                append_nav(item, ' ')
                append_detail(item, ' ')

        return '\n'.join(nav_lines), '\n'.join(detail_lines)
