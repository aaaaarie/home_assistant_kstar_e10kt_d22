"""One connection and polling coordinator per device."""

import logging
from datetime import timedelta
from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .modbus import CannotConnect, KstarClient, RegisterUnavailable
from .registers import SENSORS

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
        for sensor in SENSORS:
            if not self._enabled(sensor.key, sensor.enabled_default):
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
        return values
