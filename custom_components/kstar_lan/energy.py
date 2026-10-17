"""Accumulate a counter balance without rectifying individual polling intervals."""

from dataclasses import dataclass, field
from datetime import date
from math import isfinite

ENERGY_SIGNS = {
    "house_energy": 1,
    "battery_daily_charge": 1,
    "battery_daily_discharge": -1,
    "grid_import": -1,
    "grid_export": 1,
    "pv_total_energy": -1,
}
LEGACY_KEYS = (set(ENERGY_SIGNS) - {"battery_daily_charge", "battery_daily_discharge"}) | {
    "battery_total_charge",
    "battery_total_discharge",
}


@dataclass
class EnergyBalance:
    previous: dict[str, float] = field(default_factory=dict)
    balance: float = 0
    total: float = 0
    day: date | None = None

    def update(self, counters: dict[str, float], *, day: date) -> float:
        if (
            self.previous
            and self.day == day
            and all(counters[key] >= self.previous[key] for key in ENERGY_SIGNS)
        ):
            self.balance = round(
                self.balance
                + sum(
                    sign * (counters[key] - self.previous[key])
                    for key, sign in ENERGY_SIGNS.items()
                ),
                6,
            )
            self.total = max(self.total, self.balance)
        # First sample, a different local day, or any source reset: baseline all
        # inputs together. The unobserved interval cannot be reconstructed safely.
        self.previous = dict(counters)
        self.day = day
        return self.total

    def as_dict(self) -> dict:
        return {
            "previous": dict(self.previous),
            "balance": self.balance,
            "total": self.total,
            "day": self.day.isoformat() if self.day else None,
        }

    @classmethod
    def restore(cls, data: dict | None) -> EnergyBalance:
        if not isinstance(data, dict):
            return cls()
        previous = data.get("previous")
        balance, total = data.get("balance"), data.get("total")
        if (
            not isinstance(previous, dict)
            or any(
                type(v) not in (int, float) or not isfinite(v) or v < 0 for v in previous.values()
            )
            or any(type(v) not in (int, float) or not isfinite(v) for v in (balance, total))
            or total < max(0, balance)
        ):
            return cls()
        if set(previous) == LEGACY_KEYS:
            # Preserve the published total on upgrade. Lifetime and daily origins
            # cannot be mixed; discard the old baseline and coarse-counter debt.
            return cls(balance=total, total=total)
        if set(previous) != set(ENERGY_SIGNS):
            return cls()
        try:
            day = date.fromisoformat(data["day"])
        except KeyError, TypeError, ValueError:
            return cls()
        return cls(dict(previous), balance, total, day)
