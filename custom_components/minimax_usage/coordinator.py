"""Data update coordinator for the MiniMax Usage integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

HISTORY_RETENTION = timedelta(hours=48)


def _ts_to_dt(ms: Any) -> datetime | None:
    """Convert epoch milliseconds to an aware UTC datetime."""
    if not isinstance(ms, (int, float)) or ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class MiniMaxUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll MiniMax token_plan/remains and keep a rolling usage history."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._api_key = api_key
        self._store = Store(hass, 2, f"{DOMAIN}.samples", private=True)
        # samples: [epoch_s, used_5h_pct, used_weekly_pct, interval_start_ts, weekly_start_ts]
        self.samples: list[list[Any]] = []

    async def async_load_history(self) -> None:
        try:
            raw = await self._store.async_load()
        except Exception:  # version mismatch / broken file -> start fresh
            _LOGGER.debug("Discarding incompatible MiniMax sample history", exc_info=True)
            return
        if not isinstance(raw, list):
            return
        cutoff = datetime.now(timezone.utc).timestamp() - HISTORY_RETENTION.total_seconds()
        self.samples = [
            s
            for s in raw
            if isinstance(s, list)
            and len(s) == 5
            and isinstance(s[0], (int, float))
            and s[0] >= cutoff
        ]

    async def async_store_history(self) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - HISTORY_RETENTION.total_seconds()
        self.samples = [s for s in self.samples if s[0] >= cutoff]
        await self._store.async_save(self.samples)

    def record_sample(self, groups: dict[str, dict[str, Any]]) -> None:
        general = groups.get("general") or {}
        used_5h = general.get("used_5h")
        used_weekly = general.get("used_weekly")
        if used_5h is None or used_weekly is None:
            return

        def _epoch(dt: Any) -> float | None:
            return dt.timestamp() if isinstance(dt, datetime) else None

        self.samples.append([
            datetime.now(timezone.utc).timestamp(),
            float(used_5h),
            float(used_weekly),
            _epoch(general.get("resets_5h")),
            _epoch(general.get("resets_weekly")),
        ])

    def usage_delta(self, value_col: int, start_col: int, window: timedelta) -> float | None:
        """Usage increments within a rolling window (percentage points).

        Within one window only positive increments count. When the window
        start changed between samples (reset), the new value counts fresh
        (we cannot know what was consumed after the last poll in the old
        window, so we do not overestimate with a full remaining share).
        """
        if not self.samples:
            return None
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window.total_seconds()
        series = [s for s in self.samples if s[0] >= cutoff]
        previous = [s for s in self.samples if s[0] < cutoff]
        if previous:
            series = [previous[-1]] + series
        if len(series) < 2:
            return 0.0
        delta = 0.0
        for prev, cur in zip(series, series[1:]):
            if prev[start_col] is not None and cur[start_col] is not None and prev[start_col] != cur[start_col]:
                delta += max(0.0, float(cur[value_col]))
            else:
                inc = float(cur[value_col]) - float(prev[value_col])
                if inc > 0:
                    delta += inc
        return round(delta, 1)

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with session.get(API_URL, headers=headers, timeout=30) as resp:
                resp.raise_for_status()
                payload = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"MiniMax API request failed: {err}") from err
        except ValueError as err:
            raise UpdateFailed("MiniMax API returned invalid JSON") from err

        if not isinstance(payload, dict):
            raise UpdateFailed("MiniMax API returned unexpected payload")

        base = payload.get("base_resp") or {}
        code = base.get("status_code", 0)
        if code != 0:
            raise UpdateFailed(
                f"MiniMax API error {code}: {base.get('status_msg', 'unknown')}"
            )

        groups: dict[str, dict[str, Any]] = {}
        for raw in payload.get("model_remains") or []:
            if not isinstance(raw, dict):
                continue
            model = str(raw.get("model_name") or "general")
            interval_pct = raw.get("current_interval_remaining_percent")
            weekly_pct = raw.get("current_weekly_remaining_percent")
            groups[model] = {
                "used_5h": None if interval_pct is None else 100 - int(interval_pct),
                "used_weekly": None if weekly_pct is None else 100 - int(weekly_pct),
                "resets_5h": _ts_to_dt(raw.get("end_time")),
                "resets_weekly": _ts_to_dt(raw.get("weekly_end_time")),
                "interval_status": raw.get("current_interval_status"),
                "weekly_status": raw.get("current_weekly_status"),
                "interval_start": _ts_to_dt(raw.get("start_time")),
                "weekly_start": _ts_to_dt(raw.get("weekly_start_time")),
            }

        if not groups:
            raise UpdateFailed("MiniMax API returned no usage groups")

        self.record_sample(groups)
        await self.async_store_history()
        return groups
