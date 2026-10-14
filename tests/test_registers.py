"""Decoder behavior and map invariants; these do not validate inverter semantics."""

import pytest

from custom_components.kstar_lan.registers import SENSOR_BY_KEY, SENSORS, RegisterSensor


@pytest.mark.parametrize(
    "raw,expected", [(550, 55.0), (530, 53.0), (0, 0), (1000, 100), (1001, None), (65535, None)]
)
def test_soc(raw, expected):
    assert SENSOR_BY_KEY["battery_soc"].decode([raw]) == expected


def test_signed_and_word_order():
    # Synthetic definitions isolate the algorithm from reference-only register claims.
    temperature = RegisterSensor("test", "Test", (10,), 0.1, signed=True)
    assert temperature.decode([0xFF9C]) == -10
    signed = RegisterSensor("test", "Test", (10,), signed=True)
    assert signed.decode([0xFFFF]) == -1
    assert signed.decode([0x8000]) == -32768
    assert signed.decode([0x7FFF]) == 32767
    high_first = RegisterSensor("test", "Test", (10, 11), 0.1)
    assert high_first.decode([1, 2]) == 6553.8
    low_first = RegisterSensor("test", "Test", (11, 10))
    assert low_first.decode([1, 2]) == 131073
    assert RegisterSensor("test", "Test", (11, 10), signed=True).decode([65535, 65535]) == -1


@pytest.mark.parametrize("words", [[], [1, 2], [-1], [65536], [None], [True]])
def test_invalid_words(words):
    assert SENSOR_BY_KEY["battery_soc"].decode(words) is None


def test_conservative_map():
    assert {s.key for s in SENSORS if s.verified} == {"battery_soc", "model_code"}
    assert all(s.count <= 16 for s in SENSORS)
    assert len(SENSORS) == len(SENSOR_BY_KEY)
    assert all(set(s.words) == set(range(s.address, s.address + s.count)) for s in SENSORS)
    assert "ac_pv" not in SENSOR_BY_KEY
    assert "grid_total_power" not in SENSOR_BY_KEY


def test_known_addresses_and_reference_only_measurements():
    # The two wire addresses have device evidence; other addresses do not.
    assert SENSOR_BY_KEY["battery_soc"].words == (3066,)
    assert SENSOR_BY_KEY["model_code"].words == (3045,)
    assert "house_power" not in SENSOR_BY_KEY
    for sensor in SENSORS:
        if sensor.key not in {"battery_soc", "model_code"}:
            assert not sensor.verified
            assert sensor.provenance


@pytest.mark.parametrize("raw,charging,discharging", [(412, 0, 412), (65114, 422, 0), (0, 0, 0)])
def test_provisional_battery_power_components(raw, charging, discharging):
    assert SENSOR_BY_KEY["battery_charging_power"].decode([raw]) == charging
    assert SENSOR_BY_KEY["battery_discharging_power"].decode([raw]) == discharging
