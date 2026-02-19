# Changelog

All notable changes to this project will be documented in this file.

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
