"""One connection and polling coordinator per device."""

import logging
from datetime import timedelta
from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .energy import EnergyBalance
from .modbus import CannotConnect, KstarClient, RegisterUnavailable
from .registers import INPUT_BY_KEY, SENSORS

_LOGGER = logging.getLogger(__name__)


class KstarCoordinator(DataUpdateCoordinator[dict[str, int | float | None]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: KstarClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.entry = entry
        self.raw: dict[str, list[int]] = {}
        self.errors: dict[str, str] = {}
        self._retry_at: dict[tuple[int, int], float] = {}
        self.energy = EnergyBalance()
        self._energy_store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.ac_pv_energy")

    async def async_load_energy(self) -> None:
        self.energy = EnergyBalance.restore(await self._energy_store.async_load())

    def _enabled(self, key: str, default: bool) -> bool:
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{self.entry.unique_id}_{key}")
        if entity_id is None:
            return default
        return registry.async_get(entity_id).disabled_by is None

    async def _async_update_data(self) -> dict[str, int | float | None]:
        values: dict[str, int | float | None] = {}
        self.raw = {}
        self.errors = {}
        successful_reads = 0
        read_results: dict[tuple[int, int], list[int]] = {}
        enabled = [s for s in SENSORS if self._enabled(s.key, s.enabled_default)]
        needed = {key for s in enabled for key in (s.sources or (s.key,))}
        # Keep coarse lifetime totals as diagnostics, without registering entities.
        for direction in ("charge", "discharge"):
            if f"battery_daily_{direction}" in needed:
                needed.add(f"battery_total_{direction}")
        sample_day = dt_util.now().date()
        for sensor in INPUT_BY_KEY.values():
            if sensor.key not in needed:
                continue
            values[sensor.key] = None
            read_range = (sensor.address, sensor.count)
            if monotonic() < self._retry_at.get(read_range, 0):
                self.errors[sensor.key] = "register_rejected_backoff"
                continue
            try:
                if read_range not in read_results:
                    read_results[read_range] = await self.client.read(*read_range)
                words = read_results[read_range]
            except RegisterUnavailable:
                self._retry_at[read_range] = monotonic() + 600
                self.errors[sensor.key] = "register_rejected"
                continue
            except CannotConnect as err:
                self.raw = {}
                self.errors = {"connection": "transport_failure"}
                raise UpdateFailed("Cannot read KSTAR device") from err
            successful_reads += 1
            self.raw[sensor.key] = words
            values[sensor.key] = sensor.decode(words)
            if values[sensor.key] is None:
                self.errors[sensor.key] = "invalid_value"
        if values and successful_reads == 0:
            raise UpdateFailed("No enabled registers could be read")
        for sensor in enabled:
            if not sensor.sources:
                continue
            values[sensor.key] = None
            if any(values.get(key) is None for key in sensor.sources):
                self.errors[sensor.key] = "source_unavailable"
                continue
            if sensor.key == "ac_pv_power":
                # KSTAR grid power is positive export, negative import.
                values[sensor.key] = max(
                    0,
                    values["house_power"]
                    - values["battery_power"]
                    + sum(values[key] for key in ("grid_r", "grid_s", "grid_t"))
                    - values["pv1_power"]
                    - values["pv2_power"],
                )
            elif sensor.key == "ac_pv_energy":
                if dt_util.now().date() != sample_day:
                    self.errors[sensor.key] = "day_changed_during_poll"
                    continue
                before = self.energy.as_dict()
                values[sensor.key] = self.energy.update(
                    {key: values[key] for key in sensor.sources}, day=sample_day
                )
                if self.energy.as_dict() != before:
                    await self._energy_store.async_save(self.energy.as_dict())
        return {s.key: values[s.key] for s in enabled}
