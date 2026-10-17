from datetime import date

import pytest

from custom_components.kstar_lan.energy import EnergyBalance

DAY = date(2026, 10, 17)
NEXT_DAY = date(2026, 10, 18)


def counters(house=100, charge=1, discharge=2, imported=30, exported=5, dc=0):
    return dict(
        house_energy=house,
        battery_daily_charge=charge,
        battery_daily_discharge=discharge,
        grid_import=imported,
        grid_export=exported,
        pv_total_energy=dc,
    )


def test_common_baseline_and_fractional_counter_balance():
    energy = EnergyBalance()
    assert energy.update(counters(), day=DAY) == 0
    # Lifetime origins cancel; a 0.1 kWh battery increment contributes immediately.
    assert energy.update(counters(charge=1.1), day=DAY) == 0.1
    assert energy.update(counters(house=103, charge=2, imported=31, exported=6, dc=1), day=DAY) == 3


def test_signed_corrections_do_not_rectify_each_interval():
    energy = EnergyBalance()
    energy.update(counters(), day=DAY)
    assert energy.update(counters(house=100.1, discharge=2.2), day=DAY) == 0
    assert energy.update(counters(house=100.3, discharge=2.2), day=DAY) == 0.1
    assert energy.update(counters(house=100.5, discharge=2.2), day=DAY) == 0.3
    # A downward correction must be repaid before counting more energy.
    assert energy.update(counters(house=100.5, discharge=2.4), day=DAY) == 0.3
    assert energy.update(counters(house=100.7, discharge=2.4), day=DAY) == 0.3
    assert energy.update(counters(house=100.9, discharge=2.4), day=DAY) == 0.5


def test_source_reset_and_restore_preserve_total():
    energy = EnergyBalance()
    energy.update(counters(), day=DAY)
    assert energy.update(counters(house=102), day=DAY) == 2
    energy = EnergyBalance.restore(energy.as_dict())
    assert energy.update(counters(house=0), day=DAY) == 2
    assert energy.update(counters(house=0.5), day=DAY) == 2.5


@pytest.mark.parametrize("charge,discharge", [(0, 0), (1.5, 2.5)])
def test_midnight_rebaseline_even_if_daily_counters_exceed_yesterday(charge, discharge):
    energy = EnergyBalance()
    energy.update(counters(), day=DAY)
    energy.update(counters(house=102), day=DAY)
    energy = EnergyBalance.restore(energy.as_dict())
    # Ignore the ambiguous interval across midnight, including a missing day-end
    # sample. Do not treat either old daily totals or new-day energy as solar.
    assert energy.update(counters(house=110, charge=charge, discharge=discharge), day=NEXT_DAY) == 2
    assert (
        energy.update(counters(house=110.1, charge=charge + 0.1, discharge=discharge), day=NEXT_DAY)
        == 2.2
    )


def test_daily_counter_reset_within_day_rebaselines_all_inputs():
    energy = EnergyBalance()
    energy.update(counters(), day=DAY)
    energy.update(counters(house=102), day=DAY)
    assert energy.update(counters(house=103, charge=0), day=DAY) == 2
    assert energy.update(counters(house=103, charge=0.1), day=DAY) == 2.1


def test_multi_day_gap_or_clock_reversal_does_not_invent_energy():
    energy = EnergyBalance()
    energy.update(counters(), day=DAY)
    energy.update(counters(house=102), day=DAY)
    for day in (date(2026, 10, 20), DAY):
        assert energy.update(counters(house=150, charge=5), day=day) == 2


def test_upgrade_preserves_total_without_mixing_lifetime_and_daily_baselines():
    legacy = counters()
    legacy["battery_total_charge"] = legacy.pop("battery_daily_charge")
    legacy["battery_total_discharge"] = legacy.pop("battery_daily_discharge")
    energy = EnergyBalance.restore({"previous": legacy, "balance": -2, "total": 0.3})
    assert energy.total == 0.3
    assert energy.previous == {}
    assert energy.update(counters(charge=0.3, discharge=0), day=DAY) == 0.3
    assert energy.update(counters(charge=0.4, discharge=0), day=DAY) == 0.4
    assert EnergyBalance.restore(energy.as_dict()).as_dict() == energy.as_dict()


@pytest.mark.parametrize("bad_day", [None, "invalid", "2026-99-01", 123])
def test_invalid_saved_date_starts_new_baseline(bad_day):
    assert (
        EnergyBalance.restore(
            {"previous": counters(), "balance": 0, "total": 0, "day": bad_day}
        ).previous
        == {}
    )


def test_invalid_saved_state_starts_new_baseline():
    assert EnergyBalance.restore({"previous": {}, "balance": 0, "total": 0}).previous == {}
    assert (
        EnergyBalance.restore(
            {"previous": counters(), "balance": float("nan"), "total": 0, "day": DAY.isoformat()}
        ).previous
        == {}
    )
