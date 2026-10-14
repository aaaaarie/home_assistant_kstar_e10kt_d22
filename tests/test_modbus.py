import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pymodbus.exceptions import ModbusException

from custom_components.kstar_lan.modbus import CannotConnect, KstarClient, RegisterUnavailable


def response(words=None, error=False, code=None):
    return SimpleNamespace(registers=words, isError=lambda: error, exception_code=code)


@pytest.fixture
def client():
    with patch("custom_components.kstar_lan.modbus.AsyncModbusTcpClient") as cls:
        wire = cls.return_value
        wire.connected = True
        wire.connect = AsyncMock(return_value=True)
        wire.read_input_registers = AsyncMock(return_value=response([550]))
        yield KstarClient("host", 502, 1), wire


async def test_only_fc04_and_reconnect(client):
    client, wire = client
    wire.connected = False
    assert await client.read(3066) == [550]
    wire.connect.assert_awaited_once()
    wire.read_input_registers.assert_awaited_once_with(3066, count=1, device_id=1)
    assert not any(call[0].startswith("write") for call in wire.mock_calls)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        response([]),
        response(None),
        response(550),
        response([65536]),
        response([550], True, 4),
    ],
)
async def test_bad_response_closes(client, bad):
    client, wire = client
    wire.read_input_registers.return_value = bad
    with pytest.raises(CannotConnect):
        await client.read(3066)
    wire.close.assert_called_once()


@pytest.mark.parametrize("error", [OSError(), TimeoutError(), ModbusException("failed")])
async def test_transport_exception(client, error):
    client, wire = client
    wire.read_input_registers.side_effect = error
    with pytest.raises(CannotConnect):
        await client.read(3066)
    wire.close.assert_called_once()


async def test_connect_failure(client):
    client, wire = client
    wire.connected = False
    wire.connect.return_value = False
    with pytest.raises(CannotConnect):
        await client.read(3066)
    wire.read_input_registers.assert_not_awaited()


async def test_illegal_register_keeps_connection(client):
    client, wire = client
    wire.read_input_registers.return_value = response(error=True, code=2)
    with pytest.raises(RegisterUnavailable):
        await client.read(3300)
    wire.close.assert_not_called()


@pytest.mark.parametrize("address,count", [(0, 17), (-1, 1), (65535, 2), (0, 0)])
async def test_bounds(client, address, count):
    client, wire = client
    with pytest.raises(ValueError):
        await client.read(address, count)
    wire.read_input_registers.assert_not_awaited()


async def test_serialization(client):
    client, wire = client
    active = 0

    async def read(*args, **kwargs):
        nonlocal active
        active += 1
        assert active == 1
        await asyncio.sleep(0)
        active -= 1
        return response([550])

    wire.read_input_registers.side_effect = read
    await asyncio.gather(client.read(3066), client.read(3045))


async def test_cancellation_closes(client):
    client, wire = client
    wire.read_input_registers.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await client.read(3066)
    wire.close.assert_called_once()
