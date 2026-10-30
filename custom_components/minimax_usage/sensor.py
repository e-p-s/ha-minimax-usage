"""Sensor platform for the MiniMax Usage integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MiniMaxUsageCoordinator


@dataclass(frozen=True, kw_only=True)
class MiniMaxSensorDescription(SensorEntityDescription):
    """Describe one usage sensor."""

    field: str
    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[MiniMaxSensorDescription, ...] = (
    MiniMaxSensorDescription(
        key="used_5h",
        field="used_5h",
        translation_key="used_5h",
        value_fn=lambda g: g["used_5h"],
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:meter-electric",
    ),
    MiniMaxSensorDescription(
        key="resets_5h",
        field="resets_5h",
        translation_key="resets_5h",
        value_fn=lambda g: g["resets_5h"],
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    MiniMaxSensorDescription(
        key="used_weekly",
        field="used_weekly",
        translation_key="used_weekly",
        value_fn=lambda g: g["used_weekly"],
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:calendar-clock",
    ),
    MiniMaxSensorDescription(
        key="resets_weekly",
        field="resets_weekly",
        translation_key="resets_weekly",
        value_fn=lambda g: g["resets_weekly"],
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensors for every usage group returned by the API."""
    coordinator: MiniMaxUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MiniMaxUsageSensor] = []
    for model, group in coordinator.data.items():
        # MiniMax docs: only non-video models have a real 5h window. The API
        # fills bogus interval data (24h day window, status 3) for video groups
        # -> only expose 5h sensors when the window is actually ~5 hours long.
        start, end = group.get("interval_start"), group.get("resets_5h")
        interval_is_real = bool(
            start
            and end
            and timedelta(hours=4.5) <= (end - start) <= timedelta(hours=5.5)
        )
        for desc in SENSOR_DESCRIPTIONS:
            if group.get(desc.field) is None:
                continue
            if desc.key.startswith("resets_5h") or desc.key == "used_5h":
                if not interval_is_real:
                    continue
            entities.append(MiniMaxUsageSensor(coordinator, entry, model, desc))
    if "general" in coordinator.data:
        entities.extend(
            [
                MiniMaxDeltaSensor(coordinator, entry, "delta_5h_1h", 1, 3, timedelta(hours=1)),
                MiniMaxDeltaSensor(coordinator, entry, "delta_5h_2h", 1, 3, timedelta(hours=2)),
                MiniMaxDeltaSensor(coordinator, entry, "delta_weekly_1h", 2, 4, timedelta(hours=1)),
            ]
        )
    async_add_entities(entities)


MODEL_LABELS = {"general": "Allgemein", "video": "Video"}


class MiniMaxUsageSensor(CoordinatorEntity[MiniMaxUsageCoordinator], SensorEntity):
    """A single MiniMax usage sensor (model group x metric)."""

    _attr_has_entity_name = True
    entity_description: MiniMaxSensorDescription

    def __init__(
        self,
        coordinator: MiniMaxUsageCoordinator,
        entry: ConfigEntry,
        model: str,
        description: MiniMaxSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._model = model
        self._attr_unique_id = f"{entry.entry_id}-{model}-{description.key}"
        self._attr_suggested_object_id = f"minimax_{model}_{description.key}"
        label = MODEL_LABELS.get(model, model.capitalize())
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id, model)},
            "name": f"MiniMax Token Plan — {label}",
            "manufacturer": "MiniMax",
            "configuration_url": "https://platform.minimax.io/console/usage",
        }

    @property
    def _group(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._model)

    @property
    def native_value(self) -> Any:
        group = self._group
        if group is None:
            return None
        return self.entity_description.value_fn(group)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        group = self._group
        if group is None:
            return {}
        return {
            "model_group": self._model,
            "interval_status": group.get("interval_status"),
            "weekly_status": group.get("weekly_status"),
            "interval_start": group.get("interval_start"),
            "weekly_start": group.get("weekly_start"),
        }


class MiniMaxDeltaSensor(CoordinatorEntity[MiniMaxUsageCoordinator], SensorEntity):
    """Rolling-window usage delta (percentage points) from the history."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-line-variant"

    def __init__(
        self,
        coordinator: MiniMaxUsageCoordinator,
        entry: ConfigEntry,
        kind: str,
        value_col: int,
        start_col: int,
        window: timedelta,
    ) -> None:
        super().__init__(coordinator)
        self._value_col = value_col
        self._start_col = start_col
        self._window = window
        self._attr_translation_key = kind
        self._attr_unique_id = f"{entry.entry_id}-general-{kind}"
        self._attr_suggested_object_id = f"minimax_general_{kind}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id, "general")},
            "name": "MiniMax Token Plan — Allgemein",
            "manufacturer": "MiniMax",
            "configuration_url": "https://platform.minimax.io/console/usage",
        }

    @property
    def native_value(self) -> float | None:
        return self.coordinator.usage_delta(self._value_col, self._start_col, self._window)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "window_hours": self._window.total_seconds() / 3600,
            "samples": len(self.coordinator.samples),
        }
