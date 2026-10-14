import socket
from types import MappingProxyType

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    dr.async_setup(instance)
    await dr.async_load(instance)
    await er.async_get(instance).async_load()
    yield instance
    await instance.async_stop(force=True)


@pytest.fixture
def entry():
    return ConfigEntry(
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        domain="kstar_lan",
        title="KSTAR LAN",
        version=1,
        minor_version=1,
        data={"host": "192.168.178.238", "port": 502, "unit_id": 1},
        options={},
        source="user",
        unique_id="192.168.178.238:502:1",
        discovery_keys=MappingProxyType({}),
        subentries_data=[],
    )


@pytest.fixture(autouse=True)
def forbid_network_connections(monkeypatch):
    """Tests must mock transport; missing patches must fail before contacting hardware."""

    def blocked(*args, **kwargs):
        raise AssertionError("Network connections are forbidden in automated tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
