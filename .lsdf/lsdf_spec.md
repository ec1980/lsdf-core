# L-SDF Agent Reference

## Sigils

| Sigil | Name | Purpose |
| :---: | :--- | :--- |
| `^` | Root | Project-level stack and global constraints |
| `@` | Entity | File, class, module, or service boundary |
| `!` | Function | Function, method, or logic flow |
| `~` | Dependency | Imports and external requirements |
| `?` | Schema | Data types and shapes |
| `$` | Annotation | Comments, notes, caveats (detail index only) |
| `#` | Route | API endpoints (HTTP/RPC) |

## Syntax

**Ownership:** Indentation encodes hierarchy. `!` under `@` is a method of that entity.

```text
depth 0 — no leading space   (top-level)
depth 1 — one leading space  (member)
depth 2 — two leading spaces (nested member)
```

**Signatures:** Omit `self`/`cls`. Omit `()` for zero-arg functions. Omit `:None`/`->None`. No spaces after commas.

```text
INDEX.lsdf       — names only:  !score_deal
INDEX.detail.lsdf — full compact: !score_deal(deal:Deal,watch:Watch,cfg:Cfg):DealScore
```

**Type aliases:**

| Alias | Type | Alias | Type |
| :---: | :--- | :---: | :--- |
| `s` | `str` | `u` | `uuid` |
| `i` | `int` | `[x]` | `list[x]` |
| `f` | `float` | `{k:v}` | `dict[k,v]` |
| `b` | `bool` | `x?` | `optional[x]` |

**Schemas:** Prefer one-line form; use multiline only when too long to diff.

```text
?User{id:u,email:s,active:b}
```

**Dependencies:** Comma-separated modules; colon-separated symbols.

```text
~os,pathlib
~pydantic:BaseModel,Field
```

**Call edges** (detail index only): comma-separated callees, ordered by first appearance. Module-level functions by name; methods qualified as `ClassName.method`.

```text
!run_watch > load_watch,load_snapshot,score_watch,render_report
!run > parse,Greeter.greet
```

**Annotations** (`$`): detail index only, one short line max.

**Continuations:** `\` at line start continues the preceding block.
