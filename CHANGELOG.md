# Changelog

All notable changes to this project will be documented in this file.

## [0.4.1] - 2026-03-03

### Fixed

- Add `_recurse=False` for object fields in schema provisioning.
- Use `/test` prefix in all test indices for better isolation.

## [0.4.0] - 2026-02-26

### Added

- Schema meta-properties (`_required`, `_default`, `_write_only`, `_read_only`,
  `_null`, `_choices`) for Python-layer validation, defaults, and read/write
  field filtering — stripped before sending schemas to Xapiand.
- `_type` alias resolution: `"json"` is accepted as an alias for `"object"` in
  schema definitions.
- Integration test suite (`test_integration.py`) that exercises the full CRUD
  lifecycle and meta-properties against a live Xapiand server.

### Changed

- 412 schema auto-provisioning now sends `_xapiand_schema` (cleaned of
  meta-properties) instead of the raw `SCHEMA` dict.

## [0.3.2] - 2026-02-26

### Fixed

- Fix document ID lookup in `save()` and `delete()`: use `_id` (Xapiand's
  returned key) with fallback to `id` for new unsaved instances.

### Added

- "Defining a Model" section in README with foreign schema example and CRUD
  operations.

## [0.3.1] - 2026-02-19

### Changed

- Bump `pyxapiand` dependency from `>=2.0.0` to `>=2.1.0`.

## [0.3.0] - 2026-02-19

### Changed

- Migrate to pyxapiand 2.0.0 async API (`async`/`await` throughout).
- Update CLAUDE.md and README.md to reflect async API.

## [0.2.0]

### Added

- Google-style docstrings to all modules, classes, and methods.
- Comprehensive test suite with 100% coverage.
- `.python-version` to pin Python 3.12.
- `.envrc` for automatic virtualenv activation via direnv.

### Fixed

- `.envrc` to use native direnv functions for virtualenv activation.

## [0.1.0]

### Added

- Initial release.
- `BaseXapianModel` base class with attribute interception, `save()`, `delete()`, and template-based dynamic index naming.
- `Manager` descriptor with `create()`, `get()`, and `filter()` query methods.
- Schema auto-provisioning on first write (HTTP 412 retry).
- `SearchResults` dataclass wrapping paginated search results.
- Optional `volatile` parameter for `Manager.get()`.
- MIT license and README with usage docs.
- `pyproject.toml` for PyPI publishing with hatchling build system.
