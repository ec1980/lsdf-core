---
version: 1.0
status: Draft
date: 2026-05-02
---

# L-SDF Specification

## Abstract

L-SDF (Latent-Structured Documentation Format) is a compact, sigil-based format for representing the structure of software repositories. It is designed for consumption by AI coding agents, enabling structural navigation and code discovery at a fraction of the token cost of reading raw source files. This document defines the sigil vocabulary, syntax rules, and file conventions of L-SDF version 1.0.

## Status of This Document

This document is a **Draft** specification. Implementations should treat it as authoritative for L-SDF 1.0 behaviour. Backwards-incompatible changes will increment the major version number.

## 1. Terminology

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

- **Sigil:** A single ASCII character that prefixes a line and encodes its semantic role.
- **Index:** An `INDEX.lsdf` file that maps the structure of a single directory.
- **Manifest:** A `project.lsdf` file that maps the top-level structure of a repository.
- **Parser:** Any tool or agent that reads and interprets `.lsdf` files.

## 2. File Conventions

- Index files MUST be named `INDEX.lsdf` and placed in the directory they describe.
- The root manifest MUST be named `project.lsdf` and placed at the repository root.
- Files MUST be UTF-8 encoded with Unix line endings.
- Blank lines SHOULD be ignored by parsers.

## 3. Sigil Vocabulary

Each non-blank line in an `.lsdf` file MUST begin with zero or more space characters followed by exactly one sigil character.

| Sigil | Name | Purpose |
| :---: | :--- | :--- |
| `^` | **Root** | Project-level stack and global constraints. |
| `@` | **Entity** | File, class, module, or service boundary. |
| `!` | **Function** | Function, method, or logic flow. |
| `~` | **Dependency** | Imports and external requirements. |
| `?` | **Schema** | Data types and shapes. |
| `$` | **Annotation** | Comments, notes, caveats, or rationale. |
| `#` | **Route** | API endpoints (HTTP/RPC). |

## 4. Syntax

### 4.1 Ownership

Indentation encodes hierarchy. A sigil indented under another sigil is a member of it (e.g., `!` under `@` is a method of that entity).

### 4.2 Indentation

Each nesting level adds exactly 1 leading space. A top-level entry has 1 space; its child has 2; a grandchild has 3; and so on. The absolute column of a sigil encodes its depth. Parsers MUST NOT assume a fixed column for any sigil type.

### 4.3 Grouping

Under `~`, multiple symbols imported from the same module MUST be expressed as `module.{sym1, sym2}`. A single import is expressed as `module.sym`. A wildcard import is expressed as `module.*`.

### 4.4 Typing

A typed binding is expressed as `name:type` (e.g., `id:uuid`, `price:float`).

### 4.5 Logic

A causal chain is expressed as `step > effect`. A conditional branch is expressed as `condition?Abort`.

### 4.6 Lists

Lines starting with `-` or `>` under a sigil are treated as nested properties or logic steps.

### 4.7 Continuations

The `\` character at the start of a line denotes a continuation of the preceding block (e.g., for multi-line CLI argument lists or long descriptions).

## 5. Normative References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — Key words for use in RFCs to indicate requirement levels.
