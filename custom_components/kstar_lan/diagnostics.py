"""Diagnostics intentionally omit endpoint and all unique identifiers."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .registers import INPUT_BY_KEY


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = entry.runtime_data
    return {
        "integration_version": "0.1.0",
        "last_update_success": coordinator.last_update_success,
        "poll_interval_seconds": coordinator.update_interval.total_seconds(),
        "raw_input_registers": coordinator.raw,
        "decoded_values": coordinator.data if coordinator.last_update_success else {},
        "errors": coordinator.errors,
        "battery_lifetime_energy_kwh": {
            key: INPUT_BY_KEY[key].decode(coordinator.raw[key]) if key in coordinator.raw else None
            for key in ("battery_total_charge", "battery_total_discharge")
        },
        "ac_pv_energy_accumulator": coordinator.energy.as_dict(),
        "ac_pv": "Calculated from internal power and counter balances; compare with Sync",
    }
