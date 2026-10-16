"""Zero-based FC04 addresses. Candidate mappings are NOT D22-verified.

Numeric facts from Solarman's kstar_hybrid.yaml (KSTAR protocol V2.5).
S/T phases and per-phase load naming: KSTAR protocol V2.9.1, table 3.1.1,
public third-party-hosted copy; applicability to D22 remains unverified.
Our word tuples list the high word first. Solarman lists multiword addresses
LOW word first (see its parser). Battery power agrees with Sync in both directions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterSensor:
    key: str
    name: str
    words: tuple[int, ...]
    scale: float = 1
    signed: bool = False
    sum_words: bool = False
    sources: tuple[str, ...] = ()
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    verified: bool = False
    assumed: bool = False
    power_component: str | None = None
    bitmap: bool = False
    minimum: float | None = None
    maximum: float | None = None
    provenance: str = "solarman_kstar_hybrid_v2.5"

    @property
    def enabled_default(self) -> bool:
        # Validation build: expose the focused overview without manual opt-in.
        return self.key in OVERVIEW_SENSOR_KEYS

    @property
    def address(self) -> int:
        return min(self.words, default=0)

    @property
    def count(self) -> int:
        if not self.words:
            return 0
        return max(self.words) - self.address + 1

    def decode(self, registers: list[int]) -> int | float | None:
        """Decode unsigned words, then two's complement over the entire width."""
        if len(registers) != self.count or any(
            type(word) is not int or not 0 <= word <= 65535 for word in registers
        ):
            return None
        if self.sum_words:
            value = sum(
                word - 65536 if self.signed and word & 0x8000 else word for word in registers
            )
        else:
            value = 0
            for address in self.words:
                value = (value << 16) | registers[address - self.address]
            bits = 16 * len(self.words)
            if self.signed and value & (1 << (bits - 1)):
                value -= 1 << bits
        decoded = round(value * self.scale, 6)
        if (self.minimum is not None and decoded < self.minimum) or (
            self.maximum is not None and decoded > self.maximum
        ):
            return None
        if self.power_component == "charging":
            return max(-decoded, 0)
        if self.power_component == "discharging":
            return max(decoded, 0)
        return decoded


# Only the wanted system overview is instantiated.
SENSORS = (
    RegisterSensor(
        "battery_soc",
        "Battery SoC",
        (3066,),
        scale=0.1,
        unit="%",
        device_class="battery",
        verified=True,
        minimum=0,
        maximum=100,
    ),
    RegisterSensor(
        "battery_power",
        "Battery power",
        (3065,),
        signed=True,
        unit="W",
        device_class="power",
        assumed=True,
    ),
    RegisterSensor(
        "battery_charging_power",
        "Battery charging power",
        (3065,),
        signed=True,
        unit="W",
        device_class="power",
        assumed=True,
        power_component="charging",
    ),
    RegisterSensor(
        "battery_discharging_power",
        "Battery discharging power",
        (3065,),
        signed=True,
        unit="W",
        device_class="power",
        assumed=True,
        power_component="discharging",
    ),
    RegisterSensor(
        "battery_temperature",
        "Battery temperature",
        (3067,),
        scale=0.1,
        signed=True,
        unit="°C",
        device_class="temperature",
        minimum=-50,
        maximum=100,
    ),
    RegisterSensor(
        "battery_total_discharge",
        "Battery discharged energy",
        (3292, 3293),
        unit="kWh",
        device_class="energy",
        state_class="total_increasing",
    ),
    RegisterSensor(
        "battery_total_charge",
        "Battery charged energy",
        (3299, 3300),
        unit="kWh",
        device_class="energy",
        state_class="total_increasing",
    ),
    RegisterSensor(
        "house_power",
        "House power",
        (3144, 3145, 3146),
        sum_words=True,
        unit="W",
        device_class="power",
        provenance="kstar_protocol_v2.9.1",
    ),
    RegisterSensor(
        "house_energy",
        "Load consumed energy",
        (3152, 3153),
        scale=0.1,
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    RegisterSensor(
        "inverter_temperature",
        "Inverter radiator temperature",
        (3055,),
        scale=0.1,
        signed=True,
        unit="°C",
        device_class="temperature",
        minimum=-50,
        maximum=150,
    ),
    RegisterSensor(
        "battery_radiator_temperature",
        "Battery radiator temperature",
        (3056,),
        scale=0.1,
        signed=True,
        unit="°C",
        device_class="temperature",
        minimum=-50,
        maximum=150,
    ),
    RegisterSensor(
        "chassis_temperature",
        "Chassis temperature",
        (3057,),
        scale=0.1,
        signed=True,
        unit="°C",
        device_class="temperature",
        minimum=-50,
        maximum=150,
    ),
    RegisterSensor("system_status", "System status code", (3046,), state_class=None),
    RegisterSensor("inverter_status", "Inverter status code", (3047,), state_class=None),
    RegisterSensor("dcdc_status", "DCDC status code", (3048,), state_class=None),
    RegisterSensor(
        "pv1_power", "DC PV1 power", (3024,), signed=True, unit="W", device_class="power"
    ),
    RegisterSensor(
        "pv2_power", "DC PV2 power", (3025,), signed=True, unit="W", device_class="power"
    ),
    RegisterSensor(
        "ac_pv_power",
        "AC PV power",
        (),
        unit="W",
        device_class="power",
        sources=(
            "house_power",
            "battery_power",
            "grid_r",
            "grid_s",
            "grid_t",
            "pv1_power",
            "pv2_power",
        ),
        provenance="calculated_energy_balance",
    ),
    RegisterSensor(
        "ac_pv_energy",
        "AC PV energy",
        (),
        unit="kWh",
        device_class="energy",
        state_class="total_increasing",
        sources=(
            "house_energy",
            "battery_total_charge",
            "battery_total_discharge",
            "grid_import",
            "grid_export",
            "pv_total_energy",
        ),
        provenance="calculated_energy_balance",
    ),
    RegisterSensor(
        "pv_total_energy",
        "PV generated energy",
        (3041, 3042),
        scale=0.1,
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    RegisterSensor(
        "alarm_flags",
        "Alarm flags (raw)",
        (3049, 3050),
        state_class=None,
        bitmap=True,
        provenance="kstar_protocol_v2.9.1",
    ),
    RegisterSensor(
        "fault_flags",
        "Fault flags (raw)",
        (3051, 3052),
        state_class=None,
        bitmap=True,
        provenance="kstar_protocol_v2.9.1",
    ),
)
SENSOR_BY_KEY = {sensor.key: sensor for sensor in SENSORS}
OVERVIEW_SENSOR_KEYS = frozenset(SENSOR_BY_KEY)

# Calculation inputs only: never registered as HA entities.
CALCULATION_INPUTS = (
    RegisterSensor("grid_r", "", (3100,), signed=True),
    RegisterSensor("grid_s", "", (3104,), signed=True),
    RegisterSensor("grid_t", "", (3108,), signed=True),
    RegisterSensor("grid_import", "", (3114, 3115), scale=0.1),
    RegisterSensor("grid_export", "", (3121, 3122), scale=0.1),
)
INPUT_BY_KEY = {s.key: s for s in (*SENSORS, *CALCULATION_INPUTS) if s.words}
