# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**xprofile** is a Python module within the Dubalu Framework that defines user profile schemas and management. It provides schema definitions for user profiles stored in Xapiand (a distributed search engine), including field types, indexing options, visibility controls, and permission-gated access via `_write_only` guards.

## Development Environment

- Python 3.12, virtual environment at `.venv/`
- Activate: `source .venv/bin/activate`
- No build system (pyproject.toml/setup.py) is configured yet

## Code Style

- Use `from __future__ import annotations` in all modules
- Use modern Python 3.12+ syntax: f-strings, PEP 695 type hints (`dict[str, Any]` not `Dict[str, Any]`), `type` aliases
- Do not use Python 2 compatibility imports (`unicode_literals`, `absolute_import`)
- Naming: `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_CASE` for constants
- Use Google-style docstrings
- Max line length: 120

## Architecture

- `src/xprofile/schemas.py` — The main module. Defines `get_profile_schema()` which returns a dictionary describing all user profile fields with their types, indexing strategies, defaults, and permission constraints. Uses `xapiand.constants` for date accuracy settings.
- `src/xprofile/xprofile.py` — Profile logic (currently empty, under development).
- Profile types: `personal`, `business`, `reseller`, `referral`, `supplier`, `mashup`, `affinity`, `dssupplier`.
- Permission-sensitive fields use `_write_only` with `CAN_MANAGE_PROFILE` permission guards.

## Schema Field Convention

Each field in the schema dict uses underscore-prefixed keys for metadata:
- `_type`: Field data type (`uuid`, `string`, `term`, `text`, `boolean`, `date`, `json`, `array/term`)
- `_index`: Indexing strategy (`terms`, `field_terms`, `field_all`, `none`)
- `_required`, `_null`, `_default`: Validation constraints
- `_write_only`: Access control — either `True` or a dict mapping HTTP methods to required permissions
- `_label`, `_help_text`: Documentation metadata
