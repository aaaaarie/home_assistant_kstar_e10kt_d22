from custom_components.kstar_lan.energy import EnergyBalance


def counters(house=100, charge=10, discharge=20, imported=30, exported=5, dc=0):
    return dict(
        house_energy=house,
        battery_total_charge=charge,
        battery_total_discharge=discharge,
        grid_import=imported,
        grid_export=exported,
        pv_total_energy=dc,
    )


def test_common_baseline_and_counter_balance():
    energy = EnergyBalance()
    assert energy.update(counters()) == 0
    # Different lifetime origins cancel; only increments contribute.
    assert energy.update(counters(house=103, charge=11, imported=31, exported=6, dc=1)) == 3


def test_coarse_counter_steps_do_not_rectify_each_interval():
    energy = EnergyBalance()
    energy.update(counters())
    assert energy.update(counters(house=100.4, discharge=21)) == 0
    assert energy.update(counters(house=101.1, discharge=21)) == 0.1
    assert energy.update(counters(house=101.5, discharge=21)) == 0.5
    # A later downward correction must be repaid before counting more energy.
    assert energy.update(counters(house=101.5, discharge=22)) == 0.5
    assert energy.update(counters(house=102.5, discharge=22)) == 0.5
    assert energy.update(counters(house=103, discharge=22)) == 1


def test_source_reset_and_restore_preserve_total():
    energy = EnergyBalance()
    energy.update(counters())
    assert energy.update(counters(house=102)) == 2
    energy = EnergyBalance.restore(energy.as_dict())
    assert energy.update(counters(house=0)) == 2
    assert energy.update(counters(house=0.5)) == 2.5


def test_invalid_saved_state_starts_new_baseline():
    assert EnergyBalance.restore({"previous": {}, "balance": 0, "total": 0}).previous == {}
    assert (
        EnergyBalance.restore(
            {"previous": counters(), "balance": float("nan"), "total": 0}
        ).previous
        == {}
    )
