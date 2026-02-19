# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**xapian_model** is a Python package that provides a lightweight, ORM-like base class for building models backed by [Xapiand](https://kronuz.io/Xapiand/) (a distributed search engine). It maps Python attribute access to Xapiand document fields, offers a descriptor-based `Manager` for querying, creating, and retrieving documents, and auto-provisions schemas on first write.

## Development Environment

- Python 3.12 (pinned via `.python-version`), virtual environment at `.venv/`
- Activation is automatic via direnv (`.envrc`); just `cd` into the project
- Build system: hatchling (configured in `pyproject.toml`)
- Dependency: `pyxapiand>=2.1.0` (async API based on `httpx.AsyncClient`)

## Code Style

- Use `from __future__ import annotations` in all modules
- Use modern Python 3.12+ syntax: f-strings, PEP 695 type hints (`dict[str, Any]` not `Dict[str, Any]`), `type` aliases
- Do not use Python 2 compatibility imports (`unicode_literals`, `absolute_import`)
- Naming: `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_CASE` for constants
- Max line length: 120
- **Docstrings**: Google-style on every module, class, and public function/method.  Include `Args`, `Returns`, `Raises`, and `Attributes` sections as applicable.  Keep the one-line summary imperative (e.g. "Retrieve a document by ID.").

## Architecture

- `src/xapian_model/__init__.py` — Package entry point with module-level docstring.
- `src/xapian_model/base.py` — Core implementation containing:
  - `_template_fields()` — Extracts placeholder names from a format-string template.
  - `SearchResults` — Dataclass wrapping paginated search results.
  - `Manager` — Descriptor providing `create`, `get`, and `filter` operations against Xapiand.
  - `BaseXapianModel` — Abstract base class that subclasses override with `INDEX_TEMPLATE` and `SCHEMA` to define concrete models.  Auto-attaches a `Manager` as `objects` on subclass creation.
