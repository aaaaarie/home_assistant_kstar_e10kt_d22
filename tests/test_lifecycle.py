from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from custom_components.kstar_lan import async_setup_entry, async_unload_entry
from custom_components.kstar_lan.modbus import CannotConnect


async def test_setup_unload(hass, entry):
    client = Mock()
    client.read = AsyncMock(
        side_effect=lambda address, count: [530] if address == 3066 else [40] * count
    )
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
    client.read = AsyncMock(
        side_effect=lambda address, count: [530] if address == 3066 else [412] * count
    )
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


async def test_obsolete_entities_removed_without_touching_overview(hass, entry):
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
    wanted = registry.async_get_or_create(
        "sensor", "kstar_lan", f"{entry.unique_id}_battery_soc", config_entry=entry
    )
    unrelated = registry.async_get_or_create(
        "sensor", "other_integration", "unrelated", config_entry=entry
    )
    client = Mock()
    client.read = AsyncMock(
        side_effect=lambda address, count: [530] if address == 3066 else [412] * count
    )
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        await async_setup_entry(hass, entry)
    assert registry.async_get(voltage.entity_id) is None
    assert registry.async_get(user_disabled.entity_id) is None
    assert client.read.await_count == 17

    assert registry.async_get(wanted.entity_id).unique_id == wanted.unique_id
    assert registry.async_get(unrelated.entity_id) is not None


async def test_overview_auto_enables_candidates_but_respects_user_disables(hass, entry):
    from homeassistant.helpers import entity_registry as er

    hass.config_entries = Mock(async_forward_entry_setups=AsyncMock())
    hass.config_entries.async_get_entry.return_value = entry
    registry = er.async_get(hass)
    candidate = registry.async_get_or_create(
        "sensor",
        "kstar_lan",
        f"{entry.unique_id}_battery_temperature",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    user_disabled = registry.async_get_or_create(
        "sensor",
        "kstar_lan",
        f"{entry.unique_id}_pv1_power",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    client = Mock()
    client.read = AsyncMock(
        side_effect=lambda address, count: [530] if address == 3066 else [40] * count
    )
    with patch("custom_components.kstar_lan.KstarClient", return_value=client):
        await async_setup_entry(hass, entry)
    assert registry.async_get(candidate.entity_id).disabled_by is None
    assert registry.async_get(user_disabled.entity_id).disabled_by == er.RegistryEntryDisabler.USER
    assert "battery_temperature" in entry.runtime_data.data
    assert "pv1_power" not in entry.runtime_data.data
    assert not any(call.args[0] == 3024 for call in client.read.await_args_list)
