"""Exercise actual HA platform forwarding and entity registration."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import config_entries, loader
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import frame
from homeassistant.helpers.data_entry_flow import FlowManagerIndexView


async def test_real_entry_and_sensor_platform(hass):
    # Load the custom integration from the same structure as a manual install.
    (Path(hass.config.config_dir) / "custom_components").symlink_to(
        Path(__file__).resolve().parents[1] / "custom_components", target_is_directory=True
    )
    loader.async_setup(hass)
    frame.async_setup(hass)
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    client = Mock()
    client.read = AsyncMock(
        side_effect=lambda address, count=1: {3066: [530], 3092: [83], 3327: [100], 3427: [90]}.get(
            address, [40] * count
        )
    )
    with (
        patch("custom_components.kstar_lan.KstarClient", return_value=client),
        patch("custom_components.kstar_lan.config_flow.KstarClient", return_value=client),
    ):
        form = await hass.config_entries.flow.async_init("kstar_lan", context={"source": "user"})
        FlowManagerIndexView(hass.config_entries.flow)._prepare_result_json(form)
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"host": "192.168.178.238", "port": 502, "unit_id": 1}
        )
        entry = result["result"]
        await hass.async_block_till_done()
        before = client.read.await_count
        duplicate = await hass.config_entries.flow.async_init(
            "kstar_lan", context={"source": "user"}
        )
        duplicate = await hass.config_entries.flow.async_configure(
            duplicate["flow_id"], {"host": "192.168.178.238", "port": 502, "unit_id": 1}
        )
        assert duplicate["type"] == "abort"
        assert duplicate["reason"] == "already_configured"
        assert client.read.await_count == before
        options = await hass.config_entries.options.async_init(entry.entry_id)
        FlowManagerIndexView(hass.config_entries.options)._prepare_result_json(options)
        await hass.config_entries.options.async_configure(
            options["flow_id"], {"scan_interval": 120}
        )
        await hass.async_block_till_done()
        assert entry.options["scan_interval"] == 120
        assert entry.runtime_data.update_interval.total_seconds() == 120
    assert entry.state is config_entries.ConfigEntryState.LOADED
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == 23
    assert all(
        not any(tag in (entity.original_name or "") for tag in ("unverified", "assumed"))
        for entity in entities
    )
    assert all(entity.entity_id.startswith("sensor.kstar_lan_") for entity in entities)
    assert sum(entity.disabled_by is None for entity in entities) == 23
    assert len({entity.device_id for entity in entities}) == 1
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    soc = next(e for e in entities if e.unique_id.endswith("_battery_soc"))
    assert hass.states.get(soc.entity_id).state == "53.0"
    for address, expected in ((3092, "83"), (3327, "100"), (3427, "90")):
        candidate = next(e for e in entities if e.unique_id.endswith(f"_ac_pv_candidate_{address}"))
        assert candidate.original_name == f"AC PV candidate {address}"
        state = hass.states.get(candidate.entity_id)
        assert state.state == expected
        assert state.attributes["unit_of_measurement"] == "W"
    assert await hass.config_entries.async_unload(entry.entry_id)
    client.close.assert_called()
