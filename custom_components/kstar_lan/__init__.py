"""Read-only local monitoring for KSTAR LAN."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_UNIT_ID, DOMAIN
from .coordinator import KstarCoordinator
from .modbus import KstarClient
from .registers import SENSORS

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    registry = er.async_get(hass)
    overview_ids = {f"{entry.unique_id}_{sensor.key}" for sensor in SENSORS}
    # This single-user validation build keeps only the wanted system overview.
    for record in er.async_entries_for_config_entry(registry, entry.entry_id):
        if record.platform != DOMAIN:
            continue
        if record.unique_id not in overview_ids:
            registry.async_remove(record.entity_id)
        elif record.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(record.entity_id, disabled_by=None)
    client = KstarClient(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_UNIT_ID])
    coordinator = KstarCoordinator(hass, entry, client)
    try:
        await coordinator.async_load_energy()
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        client.close()
        raise

    @callback
    def close_on_stop(event):
        client.close()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_on_stop))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
        entry.runtime_data.client.close()
    return unloaded
