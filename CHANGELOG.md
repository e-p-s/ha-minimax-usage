## v1.1.0 — 2026-10-30
- Multilingual: full DE/EN translations via Home Assistant standard system
- Device names now use `translation_key` + `device` translation section (was hardcoded German)
- Options-flow (API key dialog) fully translated
- Translations are preloaded during setup so device names resolve correctly on cold start
# Changelog

All notable changes to this project are documented in this file.

## [1.0.2] - 2026-10-30

### Fixed
- Correct import path for `empty_config_schema` (`homeassistant.helpers.config_validation`) — v1.0.1 failed to import on setup.

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
