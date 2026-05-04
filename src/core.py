import re

SIGILS = {'^': 'Project', '@': 'Entity', '!': 'Function', '~': 'Deps', '?': 'Schema', '$': 'Annotation', '#': 'Route'}
SCHEMA_INLINE_BUDGET = 88

_TYPE_EXPANSION = {
    's': 'str',
    'i': 'int',
    'f': 'float',
    'b': 'bool',
    'a': 'Any',
}
_TYPE_COMPACTION = {value: key for key, value in _TYPE_EXPANSION.items()}


def _expand_type(compact):
    """Recursively expand a compact L-SDF type alias to its full Python form."""
    if not compact:
        return compact
    if compact.endswith('?'):
        return f'Optional[{_expand_type(compact[:-1])}]'
    if compact.startswith('[') and compact.endswith(']'):
        return f'list[{_expand_type(compact[1:-1])}]'
    if compact.startswith('q[') and compact.endswith(']'):
        return f'Sequence[{_expand_type(compact[2:-1])}]'
    if compact.startswith('l[') and compact.endswith(']'):
        return f'Literal[{compact[2:-1]}]'
    if compact.startswith('{') and compact.endswith('}'):
        inner = compact[1:-1]
        colon = inner.find(':')
        if colon != -1:
            return f'dict[{_expand_type(inner[:colon])}, {_expand_type(inner[colon + 1:])}]'
    return _TYPE_EXPANSION.get(compact, compact)


def _expand_field(field_str):
    """Expand 'name:compacttype' to 'name: FullType'. Returns unchanged if no colon."""
    if ':' not in field_str:
        return field_str
    name, _, type_compact = field_str.partition(':')
    return f'{name.strip()}: {_expand_type(type_compact.strip())}'


def _expand_signature(sig):
    """Expand type aliases in a compact function signature 'name(arg:type,...):ret'."""
    m = re.match(r'^([^(:]+)(\(([^)]*)\))?(:(.+))?$', sig)
    if not m:
        return sig
    name = m.group(1)
    args_str = m.group(3)
    ret = m.group(5)

    result = name
    if args_str is not None:
        expanded_args = []
        for arg in args_str.split(','):
            arg = arg.strip()
            if not arg:
                continue
            if ':' in arg:
                aname, _, atype = arg.partition(':')
                expanded_args.append(f'{aname.strip()}: {_expand_type(atype.strip())}')
            else:
                expanded_args.append(arg)
        result += f"({', '.join(expanded_args)})"
    if ret:
        result += f": {_expand_type(ret.strip())}"
    return result


def _compact_imports(value):
    """Convert markdown import text back to compact L-SDF import syntax."""
    cleaned = value.replace('`', '').strip()
    if ':' in cleaned:
        module, _, symbols = cleaned.partition(':')
        compact_symbols = ",".join(
            symbol.strip() for symbol in symbols.split(',') if symbol.strip()
        )
        return f"{module.strip()}:{compact_symbols}"
    return ",".join(part.strip() for part in cleaned.split(',') if part.strip())


def _compact_type(expanded):
    """Convert expanded markdown type syntax back to compact L-SDF type syntax."""
    cleaned = expanded.strip()
    optional_match = re.match(r'^Optional\[(.+)\]$', cleaned)
    if optional_match:
        return f"{_compact_type(optional_match.group(1))}?"
    list_match = re.match(r'^list\[(.+)\]$', cleaned)
    if list_match:
        return f"[{_compact_type(list_match.group(1))}]"
    sequence_match = re.match(r'^Sequence\[(.+)\]$', cleaned)
    if sequence_match:
        return f"q[{_compact_type(sequence_match.group(1))}]"
    literal_match = re.match(r'^Literal\[(.+)\]$', cleaned)
    if literal_match:
        return f"l[{literal_match.group(1)}]"
    dict_match = re.match(r'^dict\[(.+),\s*(.+)\]$', cleaned)
    if dict_match:
        return f"{{{_compact_type(dict_match.group(1).strip())}:{_compact_type(dict_match.group(2).strip())}}}"
    return _TYPE_COMPACTION.get(cleaned, cleaned)


def _compact_schema_field(value):
    """Convert 'name: ExpandedType' markdown bullets to compact L-SDF field syntax."""
    if ':' not in value:
        return value
    name, _, field_type = value.partition(':')
    return f"{name.strip()}:{_compact_type(field_type.strip())}"


def _split_top_level_commas(value):
    """Split on commas that are not nested inside (), [], or {}."""
    parts = []
    current = []
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0

    for char in value:
        if char == ',' and depth_paren == depth_bracket == depth_brace == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue

        current.append(char)
        if char == '(':
            depth_paren += 1
        elif char == ')':
            depth_paren = max(0, depth_paren - 1)
        elif char == '[':
            depth_bracket += 1
        elif char == ']':
            depth_bracket = max(0, depth_bracket - 1)
        elif char == '{':
            depth_brace += 1
        elif char == '}':
            depth_brace = max(0, depth_brace - 1)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _compact_signature(sig):
    """Convert expanded markdown function signature back to compact L-SDF syntax."""
    match = re.match(r'^([^(:]+)(\(([^)]*)\))?(:(.+))?$', sig.strip())
    if not match:
        return sig.strip()

    name = match.group(1).strip()
    args_str = match.group(3)
    ret = match.group(5)

    result = name
    if args_str is not None:
        compact_args = []
        for arg in _split_top_level_commas(args_str):
            arg = arg.strip()
            if not arg:
                continue
            if ':' in arg:
                arg_name, _, arg_type = arg.partition(':')
                compact_args.append(f"{arg_name.strip()}:{_compact_type(arg_type.strip())}")
            else:
                compact_args.append(arg)
        result += f"({','.join(compact_args)})"
    if ret:
        result += f":{_compact_type(ret.strip())}"
    return result


def _compact_calls(value):
    """Convert markdown call list back to compact comma-separated L-SDF syntax."""
    cleaned = value.replace('`', '').strip()
    return ",".join(part.strip() for part in cleaned.split(',') if part.strip())


def _entity_label(content):
    if content.startswith("INDEX:"):
        return "DIR"
    if re.search(r'\.[A-Za-z0-9]+$', content):
        return "File"
    if re.match(r'^[A-Z][A-Za-z0-9_]*(\([^)]*\))?$', content):
        return "Class"
    if content.isidentifier():
        return "Module"
    return "Entity"


def _collapse_inline_schemas(lines):
    """Collapse short multiline schema blocks back into one-line inline schema form."""
    collapsed = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent_len = len(line) - len(stripped)

        if not stripped.startswith('?') or ':' in stripped[1:] or '{' in stripped:
            collapsed.append(line)
            i += 1
            continue

        schema_name = stripped[1:]
        child_indent = indent_len + 1
        fields = []
        j = i + 1
        can_inline = True

        while j < len(lines):
            child_line = lines[j]
            child_stripped = child_line.lstrip()
            child_indent_len = len(child_line) - len(child_stripped)

            if child_indent_len <= indent_len:
                break

            if child_indent_len != child_indent or not child_stripped.startswith('?'):
                can_inline = False
                break

            field_content = child_stripped[1:]
            if ':' not in field_content:
                can_inline = False
                break

            fields.append(field_content)
            j += 1

        if can_inline and fields:
            inline = f"{' ' * indent_len}?{schema_name}{{{','.join(fields)}}}"
            if len(inline) <= SCHEMA_INLINE_BUDGET:
                collapsed.append(inline)
                i = j
                continue

        collapsed.append(line)
        i += 1

    return collapsed


def _to_markdown_indent(raw_indent):
    return " " * (len(raw_indent) * 2)


def _to_lsdf_indent(raw_indent):
    if not raw_indent:
        return ""
    return " " * max(1, len(raw_indent) // 2)

def to_markdown(lsdf_content):
    """Expands L-SDF to Markdown."""
    md = []

    for line in lsdf_content.split('\n'):
        if not line.strip():
            continue
        clean = line.lstrip()
        raw_indent = " " * (len(line) - len(clean))
        indent = _to_markdown_indent(raw_indent)
        sigil = clean[0] if clean else ''
        content = clean[1:].strip()

        if sigil == '^':
            if indent:
                md.append(f"{indent}- **Project:** {content}")
            else:
                md.append(f"# Project: {content}")

        elif sigil == '@':
            entity_label = _entity_label(content)
            if content.startswith("INDEX:") and not indent:
                md.append(f"# DIR: {content[len('INDEX:'):]}")
            elif indent:
                md.append(f"{indent}- **{entity_label}:** {content}")
            else:
                md.append(f"## {entity_label}: {content}")

        elif sigil == '!':
            eq_idx = content.find('=')
            paren_idx = content.find('(')
            if eq_idx != -1 and (paren_idx == -1 or eq_idx < paren_idx):
                # Entry point: !cmd=module:function
                cmd, _, target = content.partition('=')
                ep_str = f"`{cmd.strip()}` → `{target.strip()}`"
                if indent:
                    md.append(f"{indent}- **Entry point:** {ep_str}")
                else:
                    md.append(f"### Entry point: {ep_str}")
            else:
                # Function, optionally with call edges: !name(args):ret > callee1,callee2
                func_part, callees_md = content, None
                if ' > ' in content:
                    func_part, _, callees_str = content.partition(' > ')
                    callees_md = ', '.join(f'`{c.strip()}`' for c in callees_str.split(','))
                func_part = _expand_signature(func_part)
                if indent:
                    md.append(f"{indent}- **Function:** {func_part}")
                    if callees_md:
                        md.append(f"{indent}  - *Calls:* {callees_md}")
                else:
                    md.append(f"### Function: {func_part}")
                    if callees_md:
                        md.append(f"  - *Calls:* {callees_md}")

        elif sigil == '?':
            brace_match = re.match(r'^(\w+)\{(.+)\}$', content)
            if brace_match:
                # Inline schema: ?Name{field:type,...}
                schema_name = brace_match.group(1)
                fields = [_expand_field(f.strip()) for f in brace_match.group(2).split(',')]
                if indent:
                    md.append(f"{indent}- **Schema:** {schema_name}")
                    for field in fields:
                        md.append(f"{indent}  - {field}")
                else:
                    md.append(f"#### Schema: {schema_name}")
                    for field in fields:
                        md.append(f"  - {field}")
            elif ':' in content:
                # Schema field line: ?name:type
                expanded = _expand_field(content)
                if indent:
                    md.append(f"{indent}  - {expanded}")
                else:
                    md.append(f"  - {expanded}")
            else:
                # Schema name only
                if indent:
                    md.append(f"{indent}- **Schema:** {content}")
                else:
                    md.append(f"#### Schema: {content}")

        elif sigil == '~':
            if content.startswith('[') and content.endswith(']'):
                dep_str = ', '.join(f'`{i.strip()}`' for i in content[1:-1].split(','))
            elif ':' in content:
                module, _, symbols = content.partition(':')
                sym_list = ', '.join(f'`{s.strip()}`' for s in symbols.split(','))
                dep_str = f"`{module.strip()}`: {sym_list}"
            else:
                dep_str = ', '.join(f'`{i.strip()}`' for i in content.split(','))
            if indent:
                md.append(f"{indent}- **Imports:** {dep_str}")
            else:
                md.append(f"**Imports:** {dep_str}")

        elif sigil == '#':
            if indent:
                md.append(f"{indent}- **Route:** `{content}`")
            else:
                md.append(f"**Route:** `{content}`")

        elif sigil == '$':
            if content.startswith('lsdf:'):
                md.append(f"\n*Generated by lsdf-core {content[5:]}*")
            else:
                if indent:
                    md.append(f"{indent}- **Note:** {content}")
                else:
                    md.append(f"**Note:** {content}")

        elif clean.startswith('\\'):
            md.append(f"{indent}  {clean[1:].strip()}")

        elif clean.startswith('-'):
            md.append(f"{indent}- {clean[1:].strip()}")

        else:
            md.append(f"{indent}- {clean}")

    return "\n".join(md)

def from_markdown(md_content):
    """Compresses Markdown to L-SDF."""
    lsdf = []
    in_code_block = False
    node_stack = []
    last_function_by_indent = {}

    header_map = {
        1: '^',
        2: '@',
        3: '!',
        4: '?',
    }
    label_prefixes = {
        '^': ('Project:',),
        '@': ('Entity:', 'Class:', 'File:', 'Module:', 'Package:', 'DIR:'),
        '!': ('Action:', 'Function:', 'Method:'),
        '?': ('Schema:',),
        '~': ('Dependencies:', 'Imports:'),
        '$': ('Annotation:', 'Note:', 'Comment:'),
        '#': ('Route:',),
    }

    for raw_line in md_content.split('\n'):
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            lsdf.append(f"\\{stripped}")
            continue

        header_match = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if header_match:
            level = len(header_match.group(1))
            content = header_match.group(2).strip()
            if level == 1 and content.startswith("DIR:"):
                lsdf.append(f"@INDEX:{content[len('DIR:'):].strip()}")
                continue

            sigil = header_map.get(level, '!')
            for prefix in label_prefixes.get(sigil, ()):
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
                    break
            if sigil == '!':
                content = _compact_signature(content)
            lsdf.append(f"{sigil}{content}")
            node_stack = [(0, sigil)]
            last_function_by_indent[0] = len(lsdf) - 1
            continue

        emphasized_match = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', stripped)
        if emphasized_match:
            label = emphasized_match.group(1).strip().lower()
            value = emphasized_match.group(2).strip()
            sigil = {
                'dependencies': '~',
                'imports': '~',
                'annotation': '$',
                'note': '$',
                'comment': '$',
                'route': '#',
            }.get(label)
            if sigil:
                if sigil == '~':
                    value = _compact_imports(value)
                elif sigil == '!':
                    value = _compact_signature(value)
                lsdf.append(f"{sigil}{value}")
                node_stack = [(0, sigil)]
                if sigil == '!':
                    last_function_by_indent[0] = len(lsdf) - 1
                continue

        bullet_match = re.match(r'^(\s*)[-*+>]\s+(.*)$', raw_line)
        if bullet_match:
            indent = _to_lsdf_indent(bullet_match.group(1))
            content = bullet_match.group(2).strip()
            while node_stack and node_stack[-1][0] >= len(indent):
                node_stack.pop()
            calls_match = re.match(r'^\*Calls:\*\s*(.+)$', content)
            if calls_match:
                function_line_idx = last_function_by_indent.get(len(indent) - 1)
                if function_line_idx is not None:
                    lsdf[function_line_idx] = (
                        f"{lsdf[function_line_idx]} > {_compact_calls(calls_match.group(1))}"
                    )
                    continue
            nested_label_match = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', content)
            if nested_label_match:
                label = nested_label_match.group(1).strip().lower()
                value = nested_label_match.group(2).strip()
                sigil = {
                    'project': '^',
                    'entity': '@',
                    'class': '@',
                    'file': '@',
                    'module': '@',
                    'package': '@',
                    'dir': '@',
                    'action': '!',
                    'function': '!',
                    'method': '!',
                    'schema': '?',
                    'dependencies': '~',
                    'imports': '~',
                    'annotation': '$',
                    'note': '$',
                    'comment': '$',
                    'route': '#',
                }.get(label)
                if sigil:
                    if sigil == '~':
                        value = _compact_imports(value)
                    elif sigil == '!':
                        value = _compact_signature(value)
                    lsdf.append(f"{indent}{sigil}{value}")
                    node_stack.append((len(indent), sigil))
                    if sigil == '!':
                        last_function_by_indent[len(indent)] = len(lsdf) - 1
                    continue

            field_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$', content)
            field_parent = next(
                ((level, sigil) for level, sigil in reversed(node_stack) if sigil in {'?', '@'}),
                None,
            )
            if field_match and field_parent:
                field_indent = " " * (field_parent[0] + 1)
                lsdf.append(f"{field_indent}?{_compact_schema_field(content)}")
                node_stack.append((len(field_indent), '?field'))
                continue

            lsdf.append(f"{indent}- {content}")
            continue

        lsdf.append(f"- {stripped}")

    return "\n".join(_collapse_inline_schemas(lsdf))
