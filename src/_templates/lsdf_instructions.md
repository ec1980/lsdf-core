<!-- LSDF:START -->
# L-SDF Protocol

Must use LSDF first if available. Read `project.lsdf`, then nearest `INDEX.lsdf`. If signatures or contracts are needed, read `INDEX.detail.lsdf`. Sigils: `^`root `@`entity `!`fn `~`dep `?`schema `#`route `$`note. Indentation encodes hierarchy. Types: `s`=str `i`=int `f`=float `b`=bool `a`=Any `[x]`=list[x] `q[x]`=Sequence[x] `l[...]`=Literal[...] `{k:v}`=dict[k,v] `x?`=optional[x]. See `.lsdf/lsdf_spec.md` for full syntax. Open source files only when implementation bodies are required. After structural edits, regenerate with `lsdf gen <dir>` and run `lsdf sync . --check`.
<!-- LSDF:END -->
