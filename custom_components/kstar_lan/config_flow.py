"""UI configuration, validated with actual FC04 replies."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .modbus import CannotConnect, KstarClient, RegisterUnavailable
from .registers import SENSOR_BY_KEY


def normalize_host(value: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not host or any(char.isspace() for char in host) or "/" in host or "://" in host:
        raise vol.Invalid("Enter a host name or IP address")
    return host


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): vol.All(str, normalize_host),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
    }
)
# UI fields must be serializable; keep custom host normalization in validation.
USER_FORM_SCHEMA = USER_SCHEMA.extend({vol.Required(CONF_HOST): str})

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=30, max=3600)
        ),
    }
)


async def validate_connection(data: dict) -> None:
    client = KstarClient(data[CONF_HOST], data[CONF_PORT], data[CONF_UNIT_ID])
    try:
        await client.read(3045)
        words = await client.read(3066)
        if SENSOR_BY_KEY["battery_soc"].decode(words) is None:
            raise RegisterUnavailable("Invalid battery SoC")
    finally:
        client.close()


class KstarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = USER_SCHEMA(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_config"
            else:
                await self.async_set_unique_id(
                    f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_UNIT_ID]}"
                )
                self._abort_if_unique_id_configured()
                try:
                    await validate_connection(data)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except RegisterUnavailable:
                    errors["base"] = "unsupported_device"
                else:
                    return self.async_create_entry(
                        title=f"KSTAR LAN ({data[CONF_HOST]})", data=data
                    )
        return self.async_show_form(step_id="user", data_schema=USER_FORM_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KstarOptionsFlow()


class KstarOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                options = OPTIONS_SCHEMA(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_config"
            else:
                return self.async_create_entry(title="", data=options)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
