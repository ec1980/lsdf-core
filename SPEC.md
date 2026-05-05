---
version: 1.1
status: Draft
date: 2026-05-03
---

# L-SDF Specification

## Abstract

L-SDF (Latent-Structured Documentation Format) is a compact, sigil-based format for representing the structure of software repositories. It is designed for consumption by AI coding agents, enabling structural navigation and code discovery at a fraction of the token cost of reading raw source files. This document defines the sigil vocabulary, syntax rules, file conventions, and generator behaviour of L-SDF version 1.1.

## Status of This Document

This document is a **Draft** specification. Implementations should treat it as authoritative for L-SDF 1.1 behaviour. Backwards-incompatible changes will increment the major version number.

## 1. Terminology

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

- **Sigil:** A single ASCII character that prefixes a line and encodes its semantic role.
- **Navigation index:** An `INDEX.lsdf` file that maps the navigable structure of a single directory.
- **Detail index:** An `INDEX.detail.lsdf` file that maps the contracts, schemas, and call edges of a single directory.
- **Manifest:** A `project.lsdf` file that maps the top-level structure of a repository.
- **Parser:** Any tool or agent that reads and interprets `.lsdf` files.

## 2. File Conventions

### 2.1 File names

- The manifest MUST be named `project.lsdf` and placed at the repository root.
- The navigation index MUST be named `INDEX.lsdf` and placed in the directory it describes.
- The detail index MUST be named `INDEX.detail.lsdf` and placed in the same directory as its paired `INDEX.lsdf`.
- Files MUST be UTF-8 encoded with Unix line endings.
- Blank lines SHOULD be ignored by parsers.

### 2.2 Two-tier index model

Generated L-SDF uses exactly two index files per indexed directory:

```text
INDEX.lsdf        — compact navigation map (what exists)
INDEX.detail.lsdf — compact contract / schema / flow map (how it connects and how to call it)
```

The intended agent workflow is:

```text
1. Read project.lsdf.
2. Read the nearest INDEX.lsdf.
3. If structure or signatures are insufficient, read INDEX.detail.lsdf.
4. Open source files only when implementation bodies are required.
5. Update both index files after structural edits.
```

Generators MUST produce both `INDEX.lsdf` and `INDEX.detail.lsdf` by default.

### 2.3 Project manifest format

`project.lsdf` captures the top-level structure of a repository. A generator SHOULD populate it with the following fields:

```text
^name:stack
 @dir:role
 ~[Framework1,Framework2]
 !cmd=module:function
$lsdf:version
```

- `^name:stack` — project name and detected language stack (e.g. `Python`, `Node`, `Go`).
- `@dir:role` — one line per significant top-level directory with a role label (e.g. `main-code`, `test-suite`, `documentation`).
- `~[...]` — major frameworks and libraries detected from dependency files.
- `!cmd=module:function` — CLI entry points from `[project.scripts]` (or equivalent). One line per command.
- `$lsdf:version` — the lsdf-core version that generated this file. Used by `lsdf init` to detect when an upgrade is needed.

### 2.4 Machine metadata

Generators SHOULD write machine metadata under `.lsdf/` at the repository root for tooling use:

```text
.lsdf/
  meta.json   — generator metadata, source file lists, source and index hashes
```

Agent-facing files (`project.lsdf`, `INDEX.lsdf`, `INDEX.detail.lsdf`) MUST NOT contain generator metadata, timestamps, hashes, token statistics, or CI bookkeeping.

`lsdf sync` SHOULD use `.lsdf/meta.json` when available to detect stale indexes efficiently, and MUST fall back to full recomputation when metadata is missing.

Example `meta.json`:

```json
{
  "generator": "lsdf-core",
  "version": "1.1.2",
  "generated_at": "2026-05-03T12:00:00Z",
  "indices": {
    "src/INDEX.lsdf": {
      "profile": "nav",
      "source_files": ["src/app.py", "src/models.py"],
      "source_hash": "a3f1c8e2b7d04591",
      "index_hash": "9c2e5f1a3b8d7042"
    },
    "src/INDEX.detail.lsdf": {
      "profile": "detail",
      "source_files": ["src/app.py", "src/models.py"],
      "source_hash": "a3f1c8e2b7d04591",
      "index_hash": "4f7a2c9e1b3d8056"
    }
  }
}
```

All paths in `indices` are relative to the repository root. `source_hash` is a SHA-256 prefix over all source files for that directory. `index_hash` is a SHA-256 prefix of the index file content. A mismatch between stored and current `source_hash` signals stale source; a mismatch in `index_hash` signals manual edits to the index.

## 3. Sigil Vocabulary

Each non-blank, non-continuation line in an `.lsdf` file MUST begin with zero or more space characters followed by exactly one sigil character.

| Sigil | Name | Purpose |
| :---: | :--- | :--- |
| `^` | **Root** | Project-level stack and global constraints. |
| `@` | **Entity** | File, class, module, or service boundary. |
| `!` | **Function** | Function, method, or logic flow. |
| `~` | **Dependency** | Imports and external requirements. |
| `?` | **Schema** | Data types and shapes. |
| `$` | **Annotation** | Comments, short docstrings, notes, caveats, or rationale. |
| `#` | **Route** | HTTP API endpoints or URL paths. |

## 4. Syntax

### 4.1 Line forms

This section summarizes the canonical line forms used by generated L-SDF. Later subsections define the detailed rules for indentation, signatures, type aliases, schemas, dependencies, call edges, and continuations.

```text
^name:stack
@entity[:role]
!fn[(arg:type,...)][:return] [> callee,...]
~module[,module...]
~module:symbol[,symbol...]
?Schema{field:type,...}
#METHOD /path [> handler]
$note
\continued text
```

Whitespace inside generated line forms SHOULD be minimized. Generators SHOULD NOT emit spaces after commas in argument lists, dependency lists, schema fields, or callee lists.

The bracket notation above is descriptive only:

- [...] means optional syntax.
- ... means repetition.
- Literal list and type-alias brackets, such as [s], are part of the L-SDF type syntax.

### 4.2 Ownership and indentation

Indentation encodes hierarchy. A sigil indented under another is a member of it (e.g., `!` under `@` is a method of that entity).

Indentation rules:

```text
depth 0 — no leading space   (top-level entries)
depth 1 — one leading space  (members of depth-0 entries)
depth 2 — two leading spaces (members of depth-1 entries)
```

Parsers MUST NOT assume a fixed column for any sigil type.

### 4.3 Compact signatures

Generated L-SDF MUST use compact signatures. The following rules apply:

- Omit `self` and `cls` parameters.
- Omit `()` for zero-argument functions (write `!run`, not `!run()`).
- Omit `:None` and `->None` return annotations.
- No spaces after commas in parameter lists.
- Use compact type aliases (see §4.4).

`INDEX.lsdf` MAY omit argument lists and return types when they are not needed for navigation:

```text
!score_deal
!find_vendor
```

`INDEX.detail.lsdf` SHOULD include compact signatures when useful:

```text
!score_deal(deal:Deal,vendor:Vendor,cfg:Cfg):DealScore
```

### 4.4 Type aliases

The following standard aliases MUST be used in generated L-SDF:

| Alias | Type |
| :---: | :--- |
| `s` | `str` |
| `i` | `int` |
| `f` | `float` |
| `b` | `bool` |
| `a` | `Any` |
| `[x]` | `list[x]` |
| `q[x]` | `Sequence[x]` |
| `l[...]` | `Literal[...]` |
| `{k:v}` | `dict[k,v]` |
| `x?` | `optional[x]` |

Generated L-SDF MUST use only the standard aliases listed above. Arbitrary per-file aliases MUST NOT be introduced.

### 4.5 Schemas

Schemas MUST appear only in `INDEX.detail.lsdf`. `INDEX.lsdf` MUST NOT include schema entries.

Prefer inline one-line schema form for compact models:

```text
?DealScore{deal_id:s,score:f,bucket:i,reasons:[s]}
```

Use multiline form only when the one-line form is too long to read or diff:

```text
?User
 ?id:uuid
 ?email:s
 ?active:b
```

### 4.6 Dependencies

A single-module import is expressed as:

```text
~os
```

Multiple modules on one line use comma-separated form with no spaces:

```text
~os,pathlib
```

Symbols imported from a module use colon-separated form:

```text
~pydantic:BaseModel,Field
~fastapi:APIRouter,Depends
```

Wildcard imports, when they must be represented, use dotted-star form:

```text
~module.*
```

`INDEX.lsdf` SHOULD include only dependencies that help understand architecture. `INDEX.detail.lsdf` MAY include more import detail. Low-value or obvious imports SHOULD be omitted from both.

In practice, `INDEX.lsdf` SHOULD prefer a reduced module-level view, while `INDEX.detail.lsdf` MAY include symbol-level imports and type-supporting dependencies that clarify public signatures, schemas, routes, decorators, and major call relationships.

### 4.7 Call edges

Generated call edges express that a function invokes or depends on other project-level functions. Callee lists use comma-separated form ordered by first appearance in the body:

```text
!caller > callee1,callee2,callee3
```

Same-file module-level functions are referenced by bare name. Methods MAY be qualified with their class name when that can be inferred directly from the call site:

```text
!run > parse,Greeter.greet
```

Generators SHOULD include only call edges they can identify with reasonable confidence. Generators MAY omit callees that cannot be resolved reliably, and MAY leave callees unqualified when module or package resolution is not reliable.

Future generators MAY qualify cross-file callees with module or file scope when resolution is reliable, for example cli.parse, models.User.from_json, or src/cli.py:parse. Cross-file qualification is optional in L-SDF v1.1 and MUST NOT be required for conformance.

Chained `>` notation (implying a causal or data-flow chain) MUST NOT be used in generated output:

```text
# DO NOT generate:
!run_watch > load_watch > load_snapshot > score_watch
```

Call edges MUST appear only in `INDEX.detail.lsdf`, not in `INDEX.lsdf`.

Generators SHOULD include call edges for:

- Entry function → major pipeline functions
- Public function → important same-file or confidently resolved project-level dependency
- Orchestrator → major subfunctions
- Factory or registry → registered implementation
- Background job → worker function

Generators MAY additionally include call edges for:

- Route → handler
- CLI command → entry function

Generators SHOULD omit call edges for:

- Standard-library calls
- External library calls unless architecturally significant
- Logging
- Trivial local helpers
- Property access
- Obvious validation calls

### 4.8 Symbol inclusion

Generators SHOULD omit symbols that do not help agent navigation. The following SHOULD be skipped by default:

- Private helpers unless architecturally important
- Dunder methods unless custom behaviour matters
- Trivial `__init__` methods
- Simple property getters and setters
- Standard logging helpers
- Test fixtures that are not reused broadly
- Tiny local validation utilities
- `__init__.py` files (package markers with no standalone logic)
- `from __future__ import` and `import __future__` (implementation directives, not real dependencies)

The following SHOULD always be included:

- Public APIs
- Routes
- CLI entrypoints
- Background workers
- Cross-file helpers
- Schemas and models
- Factories and registries
- Core pipeline stages
- Functions called by many callers

### 4.9 Continuations

Continuation lines begin with `\` and continue the textual content of the preceding line or block.

They are intended for multiline textual carryover, such as translated code blocks or long annotation text, rather than as independent semantic entries.

Parsers MAY render continuation lines as attached text associated with the preceding entry. Generated L-SDF SHOULD avoid continuations unless multiline textual carryover is necessary.

## 5. Generator Behaviour

### 5.1 Compact-only output

Generated L-SDF MUST always be compact. There is no generated verbose mode. More detail means more useful structure, contracts, schemas, and call edges — not more prose.

### 5.2 Default output

Running `lsdf gen` on a directory MUST produce both `INDEX.lsdf` and `INDEX.detail.lsdf`. Selected high-value comments and short docstrings SHOULD be included in `INDEX.detail.lsdf` as compact `$` annotations.

Generators SHOULD minimise optional flags that change detail output. Fewer generation modes means simpler agent instructions and more predictable diffs.

### 5.3 Sync

`lsdf sync` MUST detect and report stale index files. When `.lsdf/meta.json` is present, `lsdf sync` SHOULD use stored source hashes to detect stale files efficiently. When metadata is absent, `lsdf sync` MUST fall back to full recomputation.

## 6. Agent Instructions

The recommended agent instruction to include in project config files is:

```text
Must use LSDF first if available. Read project.lsdf, then nearest INDEX.lsdf. If signatures or contracts are needed, read INDEX.detail.lsdf. Sigils: ^root @entity !fn ~dep ?schema #route $note. Indentation encodes hierarchy. Types: s=str i=int f=float b=bool a=Any [x]=list[x] q[x]=Sequence[x] l[...]=Literal[...] {k:v}=dict[k,v] x?=optional[x]. See .lsdf/lsdf_spec.md for full syntax. Open source files only when implementation bodies are required. After structural edits, regenerate with lsdf gen <dir> and run lsdf sync . --check.
```

Long tutorials or philosophy sections MUST NOT be added to agent-loaded instructions. Extended documentation belongs in `.lsdf/lsdf_spec.md` within the target project, generated by `lsdf init`.

## 7. Normative References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — Key words for use in RFCs to indicate requirement levels.
