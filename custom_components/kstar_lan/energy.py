"""Accumulate a counter balance without rectifying individual polling intervals."""

from dataclasses import dataclass, field
from math import isfinite

ENERGY_SIGNS = {
    "house_energy": 1,
    "battery_total_charge": 1,
    "battery_total_discharge": -1,
    "grid_import": -1,
    "grid_export": 1,
    "pv_total_energy": -1,
}


@dataclass
class EnergyBalance:
    previous: dict[str, float] = field(default_factory=dict)
    balance: float = 0
    total: float = 0

    def update(self, counters: dict[str, float]) -> float:
        if self.previous and all(counters[key] >= self.previous[key] for key in ENERGY_SIGNS):
            self.balance = round(
                self.balance
                + sum(
                    sign * (counters[key] - self.previous[key])
                    for key, sign in ENERGY_SIGNS.items()
                ),
                6,
            )
            self.total = max(self.total, self.balance)
        # First sample or any source reset: establish a common baseline without
        # counting the discontinuity as production. Keep the accumulated result.
        self.previous = dict(counters)
        return self.total

    def as_dict(self) -> dict:
        return {"previous": dict(self.previous), "balance": self.balance, "total": self.total}

    @classmethod
    def restore(cls, data: dict | None) -> EnergyBalance:
        if not isinstance(data, dict):
            return cls()
        previous = data.get("previous")
        balance, total = data.get("balance"), data.get("total")
        if (
            not isinstance(previous, dict)
            or set(previous) != set(ENERGY_SIGNS)
            or any(
                type(v) not in (int, float) or not isfinite(v) or v < 0 for v in previous.values()
            )
            or any(type(v) not in (int, float) or not isfinite(v) for v in (balance, total))
            or total < max(0, balance)
        ):
            return cls()
        return cls(dict(previous), balance, total)
