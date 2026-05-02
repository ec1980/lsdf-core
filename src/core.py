import re

SIGILS = {'^': 'Project', '@': 'Entity', '!': 'Function', '~': 'Deps', '?': 'Schema', '$': 'Annotation', '#': 'Route'}


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


def _to_markdown_indent(raw_indent):
    return " " * (len(raw_indent) * 2)


def _to_lsdf_indent(raw_indent):
    if not raw_indent:
        return ""
    return " " * max(1, len(raw_indent) // 2)

def to_markdown(lsdf_content):
    """Expands L-SDF to Markdown."""
    md = []
    heading_map = {'^': '# Project:', '!': '### Function:', '?': '#### Schema:', '~': '**Dependencies:**', '$': '**Annotation:**', '#': '### Route:'}
    nested_label_map = {'^': 'Project', '!': 'Function', '?': 'Schema', '~': 'Dependencies', '$': 'Annotation', '#': 'Route'}
    
    for line in lsdf_content.split('\n'):
        if not line.strip():
            continue
        clean = line.lstrip()
        indent = _to_markdown_indent(" " * (len(line) - len(clean)))
        sigil = clean[0] if clean else ''
        
        if sigil == '@':
            content = clean[1:].strip()
            entity_label = _entity_label(content)
            if content.startswith("INDEX:") and not indent:
                md.append(f"# DIR: {content[len('INDEX:'):]}")
            elif indent:
                md.append(f"{indent}- **{entity_label}:** {content}")
            else:
                md.append(f"## {entity_label}: {content}")
        elif sigil in heading_map:
            content = clean[1:].strip()
            if indent:
                md.append(f"{indent}- **{nested_label_map[sigil]}:** {content}")
            else:
                md.append(f"{heading_map[sigil]} {content}")
        elif clean.startswith('\\'):
            md.append(f"{indent}  {clean[1:].strip()}") # Block continuation
        elif clean.startswith('-') or clean.startswith('>'):
            md.append(f"{indent}- {clean[1:].strip()}")
        else:
            md.append(f"{indent}- {clean}") # Fallback list
            
    return "\n".join(md)

def from_markdown(md_content):
    """Compresses Markdown to L-SDF."""
    lsdf = []
    in_code_block = False

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
        '~': ('Dependencies:',),
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
            lsdf.append(f"{sigil}{content}")
            continue

        emphasized_match = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', stripped)
        if emphasized_match:
            label = emphasized_match.group(1).strip().lower()
            value = emphasized_match.group(2).strip()
            sigil = {
                'dependencies': '~',
                'annotation': '$',
                'note': '$',
                'comment': '$',
                'route': '#',
            }.get(label)
            if sigil:
                lsdf.append(f"{sigil}{value}")
                continue

        bullet_match = re.match(r'^(\s*)[-*+>]\s+(.*)$', raw_line)
        if bullet_match:
            indent = _to_lsdf_indent(bullet_match.group(1))
            content = bullet_match.group(2).strip()
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
                    'annotation': '$',
                    'note': '$',
                    'comment': '$',
                    'route': '#',
                }.get(label)
                if sigil:
                    lsdf.append(f"{indent}{sigil}{value}")
                    continue

            lsdf.append(f"{indent}- {content}")
            continue

        lsdf.append(f"- {stripped}")

    return "\n".join(lsdf)
