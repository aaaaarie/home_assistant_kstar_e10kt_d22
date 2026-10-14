from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kstar_lan.coordinator import KstarCoordinator
from custom_components.kstar_lan.diagnostics import async_get_config_entry_diagnostics
from custom_components.kstar_lan.modbus import CannotConnect, RegisterUnavailable
from custom_components.kstar_lan.registers import SENSOR_BY_KEY
from custom_components.kstar_lan.sensor import KstarSensor


@pytest.fixture
def coordinator(hass, entry):
    client = Mock()
    client.read = AsyncMock(side_effect=lambda address, count: [530] if address == 3066 else [40])
    coordinator = KstarCoordinator(hass, entry, client)
    entry.runtime_data = coordinator
    return coordinator


async def test_default_reads_and_device(coordinator):
    coordinator.data = await coordinator._async_update_data()
    assert coordinator.data["battery_soc"] == 53
    assert "model_code" not in coordinator.data
    assert coordinator.client.read.await_count == 2
    soc = KstarSensor(coordinator, SENSOR_BY_KEY["battery_soc"])
    model = KstarSensor(coordinator, SENSOR_BY_KEY["model_code"])
    assert soc.available
    assert soc.native_value == 53
    assert soc.device_info == model.device_info
    assert soc.entity_registry_enabled_default
    candidate = KstarSensor(coordinator, SENSOR_BY_KEY["battery_power"])
    assert candidate.entity_registry_enabled_default
    assert candidate.available
    assert "assumed" in candidate.name


async def test_registry_enable_backoff_and_recovery(coordinator, hass, entry):
    registry = er.async_get(hass)
    record = registry.async_get_or_create("sensor", "kstar_lan", f"{entry.unique_id}_battery_power")

    async def read(address, count):
        if address == 3065:
            raise RegisterUnavailable()
        return [530] if address == 3066 else [40]

    coordinator.client.read.side_effect = read
    coordinator.data = await coordinator._async_update_data()
    assert coordinator.data["battery_power"] is None
    assert coordinator.errors["battery_power"] == "register_rejected"
    coordinator.client.read.reset_mock()
    await coordinator._async_update_data()
    assert coordinator.client.read.await_count == 1
    coordinator._retry_at[(3065, 1)] = 0
    coordinator.client.read.side_effect = lambda address, count: (
        [65535] if address == 3065 else ([530] if address == 3066 else [40])
    )
    coordinator.data = await coordinator._async_update_data()
    assert coordinator.data["battery_power"] == -1
    registry.async_update_entity(record.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    coordinator.data = await coordinator._async_update_data()
    assert "battery_power" not in coordinator.data


async def test_failed_refresh_hides_stale_values(coordinator):
    await coordinator.async_refresh()
    entity = KstarSensor(coordinator, SENSOR_BY_KEY["battery_soc"])
    assert entity.available
    coordinator.client.read.side_effect = CannotConnect()
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert not entity.available
    assert not coordinator.raw
    coordinator.client.read.side_effect = lambda address, count: [540] if address == 3066 else [40]
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert entity.available
    assert entity.native_value == 54


async def test_invalid_soc_only_unavailable(coordinator):
    coordinator.client.read.side_effect = lambda address, count: (
        [65535] if address == 3066 else [40]
    )
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert not KstarSensor(coordinator, SENSOR_BY_KEY["battery_soc"]).available
    assert KstarSensor(coordinator, SENSOR_BY_KEY["battery_power"]).available


async def test_all_rejected(coordinator):
    coordinator.client.read.side_effect = RegisterUnavailable()
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_diagnostics_redacted(coordinator, hass, entry):
    await coordinator.async_refresh()
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert "192.168" not in str(diagnostics)
    assert diagnostics["raw_input_registers"]["battery_soc"] == [530]
    coordinator.last_update_success = False
    assert not (await async_get_config_entry_diagnostics(hass, entry))["decoded_values"]


async def test_raw_alarm_bits_and_unavailability(coordinator, hass, entry):
    registry = er.async_get(hass)
    registry.async_get_or_create("sensor", "kstar_lan", f"{entry.unique_id}_alarm_flags")
    coordinator.client.read.side_effect = lambda address, count: (
        [1, 5] if address == 3049 else ([530] if address == 3066 else [412])
    )
    await coordinator.async_refresh()
    entity = KstarSensor(coordinator, SENSOR_BY_KEY["alarm_flags"])
    assert entity.native_value == 65541
    assert entity.extra_state_attributes["raw_hex"] == "0x00010005"
    assert entity.extra_state_attributes["active_bits"] == [0, 2, 16]
    assert entity.extra_state_attributes["severity_mapping"] == "unverified"
    coordinator.client.read.side_effect = CannotConnect()
    await coordinator.async_refresh()
    assert not entity.available
    assert "active_bits" not in entity.extra_state_attributes
