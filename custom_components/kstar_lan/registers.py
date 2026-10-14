"""Zero-based FC04 addresses. Candidate mappings are NOT D22-verified.

Numeric facts from Solarman's kstar_hybrid.yaml (KSTAR protocol V2.5).
S/T phases and per-phase load naming: KSTAR protocol V2.9.1, table 3.1.1,
public third-party-hosted copy; applicability to D22 remains unverified.
Our word tuples list the high word first. Solarman lists multiword addresses
LOW word first (see its parser). Battery positive-discharge direction has one
app comparison; negative-charge direction is a provisional assumption.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterSensor:
    key: str
    name: str
    words: tuple[int, ...]
    scale: float = 1
    signed: bool = False
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    verified: bool = False
    assumed: bool = False
    power_component: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    provenance: str = "solarman_kstar_hybrid_v2.5"

    @property
    def enabled_default(self) -> bool:
        return self.verified or self.assumed

    @property
    def address(self) -> int:
        return min(self.words)

    @property
    def count(self) -> int:
        return max(self.words) - self.address + 1

    def decode(self, registers: list[int]) -> int | float | None:
        """Decode unsigned words, then two's complement over the entire width."""
        if len(registers) != self.count or any(
            type(word) is not int or not 0 <= word <= 65535 for word in registers
        ):
            return None
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


SENSORS = (
    RegisterSensor(
        "battery_soc",
        "Battery SoC",
        (3066,),
        0.1,
        unit="%",
        device_class="battery",
        verified=True,
        minimum=0,
        maximum=100,
    ),
    RegisterSensor("model_code", "Model code", (3045,), state_class=None, verified=True),
    RegisterSensor(
        "battery_voltage", "Battery voltage", (3063,), 0.01, unit="V", device_class="voltage"
    ),
    RegisterSensor(
        "battery_current",
        "Battery current (direction unverified)",
        (3064,),
        0.1,
        signed=True,
        unit="A",
        device_class="current",
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
        0.1,
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
        "grid_import_energy",
        "Grid imported energy",
        (3114, 3115),
        0.1,
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    RegisterSensor(
        "grid_export_energy",
        "Grid exported energy",
        (3121, 3122),
        0.1,
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    RegisterSensor(
        "load_r_power",
        "Load R-phase power",
        (3144,),
        unit="W",
        device_class="power",
        provenance="kstar_protocol_v2.9.1",
    ),
    RegisterSensor(
        "house_energy",
        "Load consumed energy",
        (3152, 3153),
        0.1,
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    RegisterSensor(
        "grid_r_voltage", "Grid R-phase voltage", (3097,), 0.1, unit="V", device_class="voltage"
    ),
    RegisterSensor(
        "grid_r_frequency",
        "Grid R-phase frequency",
        (3098,),
        0.01,
        unit="Hz",
        device_class="frequency",
    ),
    RegisterSensor(
        "grid_r_current",
        "Grid R-phase meter current",
        (3099,),
        0.001,
        signed=True,
        unit="A",
        device_class="current",
    ),
    RegisterSensor(
        "grid_r_power",
        "Grid R-phase power (direction unverified)",
        (3100,),
        signed=True,
        unit="W",
        device_class="power",
    ),
    RegisterSensor(
        "inverter_r_voltage",
        "Inverter R-phase voltage",
        (3123,),
        0.1,
        unit="V",
        device_class="voltage",
    ),
    RegisterSensor(
        "inverter_r_current",
        "Inverter R-phase current",
        (3124,),
        0.01,
        signed=True,
        unit="A",
        device_class="current",
    ),
    RegisterSensor(
        "inverter_r_frequency",
        "Inverter R-phase frequency",
        (3125,),
        0.01,
        unit="Hz",
        device_class="frequency",
    ),
    RegisterSensor(
        "inverter_r_power",
        "Inverter R-phase power",
        (3126,),
        signed=True,
        unit="W",
        device_class="power",
    ),
    RegisterSensor(
        "inverter_temperature",
        "Inverter radiator temperature",
        (3055,),
        0.1,
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
        0.1,
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
        0.1,
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
)
# Only addresses explicitly listed in protocol table 3.1.1; no inferred offsets.
for phase, grid_base, inverter_base, load_address in (
    ("s", 3101, 3127, 3145),
    ("t", 3105, 3131, 3146),
):
    phase_name = phase.upper()
    SENSORS += (
        RegisterSensor(
            f"grid_{phase}_voltage",
            f"Grid {phase_name}-phase voltage",
            (grid_base,),
            0.1,
            unit="V",
            device_class="voltage",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"grid_{phase}_frequency",
            f"Grid {phase_name}-phase frequency",
            (grid_base + 1,),
            0.01,
            unit="Hz",
            device_class="frequency",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"grid_{phase}_current",
            f"Grid {phase_name}-phase meter current",
            (grid_base + 2,),
            0.001,
            signed=True,
            unit="A",
            device_class="current",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"grid_{phase}_power",
            f"Grid {phase_name}-phase power (direction unverified)",
            (grid_base + 3,),
            signed=True,
            unit="W",
            device_class="power",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"inverter_{phase}_voltage",
            f"Inverter {phase_name}-phase voltage",
            (inverter_base,),
            0.1,
            unit="V",
            device_class="voltage",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"inverter_{phase}_current",
            f"Inverter {phase_name}-phase current",
            (inverter_base + 1,),
            0.01,
            signed=True,
            unit="A",
            device_class="current",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"inverter_{phase}_frequency",
            f"Inverter {phase_name}-phase frequency",
            (inverter_base + 2,),
            0.01,
            unit="Hz",
            device_class="frequency",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"inverter_{phase}_power",
            f"Inverter {phase_name}-phase power",
            (inverter_base + 3,),
            signed=True,
            unit="W",
            device_class="power",
            provenance="kstar_protocol_v2.9.1",
        ),
        RegisterSensor(
            f"load_{phase}_power",
            f"Load {phase_name}-phase power",
            (load_address,),
            unit="W",
            device_class="power",
            provenance="kstar_protocol_v2.9.1",
        ),
    )
SENSOR_BY_KEY = {sensor.key: sensor for sensor in SENSORS}
