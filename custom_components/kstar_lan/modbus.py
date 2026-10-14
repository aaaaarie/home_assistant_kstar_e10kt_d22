"""Serialized, bounded FC04 reads; no write API is exposed."""

import asyncio

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException


class CannotConnect(Exception):
    """Transport failure (including malformed/short responses)."""


class RegisterUnavailable(Exception):
    """Device rejected a specific register range."""


class KstarClient:
    def __init__(self, host: str, port: int, unit_id: int) -> None:
        self._client = AsyncModbusTcpClient(host, port=port, timeout=3, retries=0)
        self._unit_id = unit_id
        self._lock = asyncio.Lock()

    async def read(self, address: int, count: int = 1) -> list[int]:
        if not 0 <= address <= 65535 or not 1 <= count <= 16 or address + count > 65536:
            raise ValueError("Read outside bounded register range")
        async with self._lock:
            try:
                if not self._client.connected and not await self._client.connect():
                    raise CannotConnect("Connection failed")
                response = await self._client.read_input_registers(
                    address, count=count, device_id=self._unit_id
                )
                if response is None:
                    raise CannotConnect("Missing response")
                if response.isError():
                    if getattr(response, "exception_code", None) in (1, 2, 3):
                        raise RegisterUnavailable("Register rejected")
                    raise CannotConnect("Modbus error response")
                words = getattr(response, "registers", None)
                if (
                    not isinstance(words, (list, tuple))
                    or len(words) != count
                    or any(type(w) is not int or not 0 <= w <= 65535 for w in words)
                ):
                    raise CannotConnect("Malformed response")
                return list(words)
            except (OSError, TimeoutError, ModbusException) as err:
                self.close()
                raise CannotConnect("Transport error") from err
            except CannotConnect:
                self.close()
                raise
            except asyncio.CancelledError:
                self.close()
                raise

    def close(self) -> None:
        self._client.close()
