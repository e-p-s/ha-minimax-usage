# MiniMax Usage for Home Assistant

Custom integration exposing your **MiniMax token plan** quota in Home Assistant — including rolling consumption deltas (last hour / last 2 hours).

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/e-p-s/ha-minimax-usage.svg)](https://github.com/e-p-s/ha-minimax-usage/releases)
[![Validate with hassfest](https://github.com/e-p-s/ha-minimax-usage/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/e-p-s/ha-minimax-usage/actions/workflows/hassfest.yaml)
[![HACS Validation](https://github.com/e-p-s/ha-minimax-usage/actions/workflows/validate.yaml/badge.svg)](https://github.com/e-p-s/ha-minimax-usage/actions/workflows/validate.yaml)
[![License: MIT](https://img.shields.io/github/license/e-p-s/ha-minimax-usage.svg)](LICENSE)
![hassfest](https://github.com/e-p-s/ha-minimax-usage/actions/workflows/hassfest.yaml/badge.svg)

## What it does

Polls `https://www.minimax.io/v1/token_plan/remains` every 60 s and creates:

| Sensor | Type | Description |
|---|---|---|
| 5h usage | % | Usage in the current 5-hour window |
| 5h reset | timestamp | End of the current 5h window |
| Weekly usage | % | Usage in the current weekly window |
| Weekly reset | timestamp | End of the current weekly window |
| Δ 5h usage last hour / 2 hours | percentage points | Rolling-window consumption |
| Δ weekly usage last hour | percentage points | Rolling-window consumption |

A second device **“— Video”** exposes the weekly sensors for the `video` model group. The misleading "5h" value the API returns for video (it is actually a 24 h window) is intentionally hidden.

### How the delta sensors work

Every poll is stored as a sample in a rolling 48 h history (`.storage/minimax_usage.samples`, private file). Deltas are computed from sample differences. When the time window resets between two samples, only the new value counts as increment — resets never produce phantom consumption. History starts empty; all windows are filled after ~1–2 h of polling.

## Requirements

- Home Assistant ≥ 2024.12 (tested on 2026.10)
- An active MiniMax token/subscription plan
- A subscription API key from [platform.minimax.io](https://platform.minimax.io)

## Installation

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=minimax_usage)

*Requires the integration to be installed first (HACS or manual).*

### HACS (custom repository)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=e-p-s&repository=ha-minimax-usage&category=integration)


### HACS (custom repository)

1. HACS → Integrations → ⋮ (top right) → **Custom repositories**
2. Add `https://github.com/e-p-s/ha-minimax-usage`, category **Integration**
3. Install → restart Home Assistant

### Manual

1. Copy `custom_components/minimax_usage/` to `/config/custom_components/`
2. Restart Home Assistant (a full restart, not just a reload)

## Configuration

Settings → Devices & Services → Add Integration → **“MiniMax Usage”** → paste your API key.
The key stays editable afterwards via the integration's **Configure** (gear) button.

## Privacy

- The API key is stored only in the local config entry (`.storage`, private).
- The only outbound calls go to `minimax.io`.
- The sample history contains percentage values only.

## Troubleshooting

| Problem | Cause / fix |
|---|---|
| Integration not in the search list | Full restart required after first install |
| Entry shows an error | Restart Core; check Settings → System → Logs |
| Deltas stay 0 | History needs to build up (≥ 1–2 h) |

## License

MIT — see [LICENSE](LICENSE).
