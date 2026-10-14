from unittest.mock import AsyncMock, Mock, patch

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import AbortFlow

from custom_components.kstar_lan.config_flow import (
    OPTIONS_SCHEMA,
    USER_SCHEMA,
    KstarConfigFlow,
    KstarOptionsFlow,
    validate_connection,
)
from custom_components.kstar_lan.modbus import CannotConnect, RegisterUnavailable

DATA = {"host": "192.168.178.238", "port": 502, "unit_id": 1}


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", ""),
        ("host", None),
        ("host", 123),
        ("host", "http://host"),
        ("port", 0),
        ("port", 65536),
        ("unit_id", 0),
        ("unit_id", 248),
    ],
)
def test_invalid_config(field, value):
    with pytest.raises(vol.Invalid):
        USER_SCHEMA(DATA | {field: value})


def test_defaults_normalization_and_options():
    assert USER_SCHEMA({"host": "  Inverter.LOCAL. "}) == DATA | {"host": "inverter.local"}
    assert OPTIONS_SCHEMA({}) == {"scan_interval": 60}
    for interval in (29, 3601):
        with pytest.raises(vol.Invalid):
            OPTIONS_SCHEMA({"scan_interval": interval})


@pytest.mark.parametrize("error", [None, CannotConnect(), RegisterUnavailable()])
async def test_probe_closes(error):
    with patch("custom_components.kstar_lan.config_flow.KstarClient") as cls:
        client = cls.return_value
        client.read = AsyncMock(side_effect=error if error else [[40], [550]])
        if error:
            with pytest.raises(type(error)):
                await validate_connection(DATA)
        else:
            await validate_connection(DATA)
            assert client.read.await_count == 2
        client.close.assert_called_once()


async def test_invalid_soc_rejected():
    with patch("custom_components.kstar_lan.config_flow.KstarClient") as cls:
        cls.return_value.read = AsyncMock(side_effect=[[40], [65535]])
        with pytest.raises(RegisterUnavailable):
            await validate_connection(DATA)
        cls.return_value.close.assert_called_once()


@pytest.mark.parametrize(
    "error,expected",
    [
        (CannotConnect(), "cannot_connect"),
        (RegisterUnavailable(), "unsupported_device"),
        (None, None),
    ],
)
async def test_user_flow(hass, error, expected):
    flow = KstarConfigFlow()
    flow.hass = hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock()
    with patch(
        "custom_components.kstar_lan.config_flow.validate_connection", AsyncMock(side_effect=error)
    ):
        result = await flow.async_step_user(DATA)
    if expected:
        assert result["errors"]["base"] == expected
    else:
        assert result["data"] == DATA
    flow.async_set_unique_id.assert_awaited_once_with("192.168.178.238:502:1")


async def test_duplicate_stops_before_network(hass):
    flow = KstarConfigFlow()
    flow.hass = hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock(side_effect=AbortFlow("already_configured"))
    with patch("custom_components.kstar_lan.config_flow.validate_connection", AsyncMock()) as probe:
        with pytest.raises(AbortFlow):
            await flow.async_step_user(DATA)
        probe.assert_not_awaited()


async def test_options_flow(hass):
    flow = KstarOptionsFlow()
    flow.hass = hass
    assert (await flow.async_step_init({"scan_interval": 120}))["data"] == {"scan_interval": 120}
