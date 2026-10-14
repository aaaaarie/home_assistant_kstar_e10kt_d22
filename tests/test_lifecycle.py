from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from custom_components.kstar_lan import async_setup_entry, async_unload_entry
from custom_components.kstar_lan.modbus import CannotConnect


async def test_setup_unload(hass, entry):
    client = Mock()
    client.read = AsyncMock(side_effect=lambda address, count: [530] if address == 3066 else [40])
    manager = Mock()
    manager.async_forward_entry_setups = AsyncMock()
    manager.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries = manager
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        assert await async_setup_entry(hass, entry)
    manager.async_forward_entry_setups.assert_awaited_once()
    assert entry.runtime_data.data["battery_soc"] == 53
    assert await async_unload_entry(hass, entry)
    client.close.assert_called_once()
    assert entry.runtime_data._shutdown_requested


async def test_shutdown_closes_connection(hass, entry):
    client = Mock()
    client.read = AsyncMock(side_effect=[[530], [412]])
    hass.config_entries = Mock(async_forward_entry_setups=AsyncMock())
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        await async_setup_entry(hass, entry)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    client.close.assert_called_once()


async def test_setup_failure_closes_and_retries(hass, entry):
    client = Mock()
    client.read = AsyncMock(side_effect=CannotConnect())
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)
    client.close.assert_called_once()


async def test_unload_failure_keeps_connection(hass, entry):
    client = Mock()
    entry.runtime_data = Mock(client=client)
    hass.config_entries = Mock(async_unload_platforms=AsyncMock(return_value=False))
    assert not await async_unload_entry(hass, entry)
    client.close.assert_not_called()


async def test_deferred_entities_disabled_without_deleting_history(hass, entry):
    from homeassistant.helpers import entity_registry as er

    hass.config_entries = Mock(async_forward_entry_setups=AsyncMock())
    hass.config_entries.async_get_entry.return_value = entry
    registry = er.async_get(hass)
    voltage = registry.async_get_or_create(
        "sensor", "kstar_lan", f"{entry.unique_id}_battery_voltage", config_entry=entry
    )
    user_disabled = registry.async_get_or_create(
        "sensor",
        "kstar_lan",
        f"{entry.unique_id}_battery_current",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    client = Mock()
    client.read = AsyncMock(side_effect=lambda address, count: [530] if address == 3066 else [412])
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        await async_setup_entry(hass, entry)
    assert registry.async_get(voltage.entity_id).disabled_by == er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(user_disabled.entity_id).disabled_by == er.RegistryEntryDisabler.USER
    assert client.read.await_count == 2
    assert registry.async_get(voltage.entity_id).unique_id == voltage.unique_id
