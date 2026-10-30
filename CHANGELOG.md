# Changelog

All notable changes to this project are documented in this file.

## [1.0.1] - 2026-10-30

### Fixed
- Manifest keys sorted to satisfy hassfest.
- Declared an empty `CONFIG_SCHEMA` (config-entry-only integration).

## [1.0.0] - 2026-10-30

### Added
- Config-flow based integration (API key entered in the UI, editable via options dialog).
- Usage sensors polled from the provider API.
- Rolling-window delta sensors backed by a persistent 48 h sample history (`.storage`, private).
- German and English sensor translations.
