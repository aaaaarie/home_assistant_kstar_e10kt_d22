from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.kstar_lan.coordinator import KstarCoordinator
from custom_components.kstar_lan.modbus import CannotConnect, RegisterUnavailable
from custom_components.kstar_lan.registers import SENSOR_BY_KEY
from custom_components.kstar_lan.sensor import KstarSensor


def set_snapshot(
    client,
    *,
    house=100,
    charge=10,
    discharge=20,
    imported=30,
    exported=5,
    dc_energy=0,
    load=1000,
    battery=400,
    grid=(-50, -25, -25),
    dc=(0, 0),
    rejected=None,
):
    words = {
        3066: 500,
        3301: round(charge * 10),
        3294: round(discharge * 10),
        3065: battery & 65535,
        3144: load,
        3145: 0,
        3146: 0,
        3100: grid[0] & 65535,
        3104: grid[1] & 65535,
        3108: grid[2] & 65535,
        3024: dc[0],
        3025: dc[1],
    }
    for address, value in (
        (3152, round(house * 10)),
        (3299, int(charge)),
        (3292, int(discharge)),
        (3114, round(imported * 10)),
        (3121, round(exported * 10)),
        (3041, round(dc_energy * 10)),
    ):
        words[address], words[address + 1] = value >> 16, value & 65535

    async def read(address, count):
        if address == rejected:
            raise RegisterUnavailable()
        return [words.get(address + i, 0) for i in range(count)]

    client.read.side_effect = read


@pytest.fixture
def coordinator(hass, entry):
    client = Mock(read=AsyncMock())
    set_snapshot(client)
    return KstarCoordinator(hass, entry, client)


@pytest.mark.parametrize(
    "load,battery,grid,dc,expected",
    [
        (1000, 400, (-50, -25, -25), (0, 0), 500),
        (300, -400, (50, 25, 25), (0, 0), 800),
        (300, -400, (50, 25, 25), (100, 200), 500),
        (200, 400, (0, 0, 0), (0, 0), 0),
    ],
)
async def test_power_balance(coordinator, load, battery, grid, dc, expected):
    set_snapshot(coordinator.client, load=load, battery=battery, grid=grid, dc=dc)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_power"] == expected
    assert not any(key.startswith("grid_") for key in coordinator.data)
    entity = KstarSensor(coordinator, SENSOR_BY_KEY["ac_pv_power"])
    assert entity.available
    assert entity.extra_state_attributes == {}
    assert all(call.args[1] <= 16 for call in coordinator.client.read.await_args_list)


async def test_counters_survive_restart_and_transport_gap(coordinator, hass, entry):
    await coordinator.async_load_energy()
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] == 0
    set_snapshot(coordinator.client, house=102)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] == 2
    restarted = KstarCoordinator(hass, entry, coordinator.client)
    await restarted.async_load_energy()
    restarted.client.read.side_effect = CannotConnect()
    await restarted.async_refresh()
    assert not KstarSensor(restarted, SENSOR_BY_KEY["ac_pv_energy"]).available
    set_snapshot(restarted.client, house=105)
    await restarted.async_refresh()
    assert restarted.data["ac_pv_energy"] == 5


async def test_missing_source_hides_result_and_preserves_baseline(coordinator):
    await coordinator.async_refresh()
    set_snapshot(coordinator.client, house=102, rejected=3152)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] is None
    assert coordinator.data["ac_pv_power"] == 500
    assert coordinator.energy.previous["house_energy"] == 100
    coordinator._retry_at[(3152, 2)] = 0
    set_snapshot(coordinator.client, house=105, rejected=3104)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_power"] is None
    assert coordinator.data["ac_pv_energy"] == 5


async def test_disabled_sources_still_feed_calculations(coordinator, hass, entry):
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "kstar_lan",
        f"{entry.unique_id}_battery_power",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await coordinator.async_refresh()
    assert "battery_power" not in coordinator.data
    assert coordinator.data["ac_pv_power"] == 500


async def test_disabling_calculations_stops_internal_grid_reads(coordinator, hass, entry):
    registry = er.async_get(hass)
    for key in ("ac_pv_power", "ac_pv_energy"):
        registry.async_get_or_create(
            "sensor",
            "kstar_lan",
            f"{entry.unique_id}_{key}",
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    await coordinator.async_refresh()
    assert not any(key.startswith("ac_pv_") for key in coordinator.data)
    assert coordinator.client.read.await_count == 20
    assert not any(
        call.args[0] in (3100, 3104, 3108, 3114, 3121)
        for call in coordinator.client.read.await_args_list
    )


async def test_fractional_battery_energy_without_lifetime_counter_change(coordinator):
    set_snapshot(coordinator.client, charge=0.3, discharge=0)
    await coordinator.async_refresh()
    assert coordinator.data["battery_daily_charge"] == 0.3
    assert coordinator.data["battery_daily_discharge"] == 0
    assert "battery_total_charge" not in coordinator.data
    assert coordinator.raw["battery_total_charge"] == [0, 0]
    set_snapshot(coordinator.client, charge=0.4, discharge=0)
    await coordinator.async_refresh()
    assert coordinator.data["battery_daily_charge"] == 0.4
    assert coordinator.data["ac_pv_energy"] == 0.1
    assert coordinator.raw["battery_total_charge"] == [0, 0]


async def test_daily_source_unavailable_preserves_baseline(coordinator):
    await coordinator.async_refresh()
    set_snapshot(coordinator.client, charge=10.1, rejected=3301)
    await coordinator.async_refresh()
    assert not KstarSensor(coordinator, SENSOR_BY_KEY["battery_daily_charge"]).available
    assert coordinator.data["ac_pv_energy"] is None
    assert coordinator.energy.previous["battery_daily_charge"] == 10
    coordinator._retry_at[(3301, 1)] = 0
    set_snapshot(coordinator.client, charge=10.2)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] == 0.2


async def test_lifetime_diagnostic_failure_does_not_block_daily_energy(coordinator):
    set_snapshot(coordinator.client, charge=0.3, rejected=3299)
    await coordinator.async_refresh()
    assert coordinator.data["battery_daily_charge"] == 0.3
    assert coordinator.data["ac_pv_energy"] == 0
    assert coordinator.errors["battery_total_charge"] == "register_rejected"


async def test_midnight_restart_preserves_total_and_rebaselines(coordinator, hass, entry):
    with patch("custom_components.kstar_lan.coordinator.dt_util.now") as now:
        now.return_value = datetime(2026, 10, 17, 23, 58)
        await coordinator.async_load_energy()
        await coordinator.async_refresh()
        set_snapshot(coordinator.client, charge=10.1)
        await coordinator.async_refresh()
        assert coordinator.data["ac_pv_energy"] == 0.1
        restarted = KstarCoordinator(hass, entry, coordinator.client)
        await restarted.async_load_energy()
        now.return_value = datetime(2026, 10, 18, 0, 1)
        set_snapshot(restarted.client, charge=0, discharge=0)
        await restarted.async_refresh()
        assert restarted.data["ac_pv_energy"] == 0.1
        set_snapshot(restarted.client, charge=0.1, discharge=0)
        await restarted.async_refresh()
        assert restarted.data["ac_pv_energy"] == 0.2


async def test_poll_spanning_midnight_does_not_save_mixed_day_counters(coordinator):
    await coordinator.async_refresh()
    previous = coordinator.energy.as_dict()
    set_snapshot(coordinator.client, charge=0)
    with patch("custom_components.kstar_lan.coordinator.dt_util.now") as now:
        now.side_effect = [datetime(2026, 10, 17, 23, 59, 59), datetime(2026, 10, 18)]
        await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] is None
    assert coordinator.errors["ac_pv_energy"] == "day_changed_during_poll"
    assert coordinator.energy.as_dict() == previous


async def test_existing_stored_ac_total_survives_upgrade(coordinator, hass, entry):
    await coordinator._energy_store.async_save(
        {
            "previous": {
                "house_energy": 28.6,
                "battery_total_charge": 6,
                "battery_total_discharge": 13,
                "grid_import": 10,
                "grid_export": 1.7,
                "pv_total_energy": 0,
            },
            "balance": -0.2,
            "total": 0.3,
        }
    )
    await coordinator.async_load_energy()
    set_snapshot(coordinator.client, charge=0.3, discharge=0)
    await coordinator.async_refresh()
    assert coordinator.data["ac_pv_energy"] == 0.3
    restarted = KstarCoordinator(hass, entry, coordinator.client)
    await restarted.async_load_energy()
    set_snapshot(restarted.client, charge=0.4, discharge=0)
    await restarted.async_refresh()
    assert restarted.data["ac_pv_energy"] == 0.4
