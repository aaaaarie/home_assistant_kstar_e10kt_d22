"""Declarative read-only entities on one KSTAR device."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KstarCoordinator
from .registers import SENSORS, RegisterSensor


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(KstarSensor(entry.runtime_data, definition) for definition in SENSORS)


class KstarSensor(CoordinatorEntity[KstarCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KstarCoordinator, definition: RegisterSensor) -> None:
        super().__init__(coordinator)
        self.definition = definition
        # Suggest a stable Recorder-filterable ID; HA retains registry overrides.
        self.entity_id = f"sensor.{DOMAIN}_{definition.key}"
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{definition.key}"
        self._attr_name = definition.name
        self._attr_native_unit_of_measurement = definition.unit
        self._attr_device_class = definition.device_class
        self._attr_state_class = definition.state_class
        self._attr_entity_registry_enabled_default = definition.enabled_default
        if definition.device_class is None:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id)},
            name="KSTAR inverter / battery",
            manufacturer="KSTAR",
            model="BlueSpark E10KT-D22",
        )
        self._attr_extra_state_attributes = (
            {}
            if definition.sources
            else {
                "register_addresses": list(definition.words),
                "modbus_function": 4,
                "scale": definition.scale,
                "provenance": definition.provenance,
                "signed": definition.signed,
                "power_component": definition.power_component,
            }
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get(self.definition.key) is not None

    @property
    def native_value(self) -> int | float | None:
        return self.coordinator.data.get(self.definition.key)

    @property
    def extra_state_attributes(self) -> dict:
        attributes = dict(self._attr_extra_state_attributes)
        if self.definition.bitmap and self.available:
            mask = int(self.native_value)
            attributes["raw_hex"] = f"0x{mask:08X}"
            attributes["active_bits"] = [bit for bit in range(32) if mask & (1 << bit)]
        return attributes
