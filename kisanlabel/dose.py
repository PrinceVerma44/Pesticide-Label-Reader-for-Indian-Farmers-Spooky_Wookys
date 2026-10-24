"""Dose maths. Done in plain Python on purpose: numbers a farmer sprays must never come
from a language model's arithmetic."""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class TankDose:
    amount: float
    unit: str
    how: str  # shows the working so the farmer or shopkeeper can check it


def dose_for_tank(use: dict, tank_litres: float) -> Optional[TankDose]:
    """How much product to put in ONE tank. Returns None if the label doesn't give enough."""
    if tank_litres <= 0:
        raise ValueError("Tank size must be more than 0 litres.")
    unit = use.get("dose_unit")
    per_litre = use.get("dose_per_litre")
    per_acre = use.get("dose_per_acre")
    water = use.get("water_per_acre_litres")

    if unit and per_litre is not None:
        return TankDose(
            round(per_litre * tank_litres, 1), unit, f"{per_litre} {unit}/L x {tank_litres:g} L"
        )
    if unit and per_acre is not None and water:
        amount = per_acre * tank_litres / water
        return TankDose(
            round(amount, 1),
            unit,
            f"{per_acre} {unit}/acre x {tank_litres:g} L tank / {water} L water per acre",
        )
    return None


def acres_per_tank(use: dict, tank_litres: float) -> Optional[float]:
    """How much land one tank covers, if the label says litres of water per acre."""
    water = use.get("water_per_acre_litres")
    if not water:
        return None
    return round(tank_litres / water, 2)


def safe_harvest_date(spray_date: date, waiting_days: Optional[float]) -> Optional[date]:
    """Earliest harvest date given the label's waiting period (pre-harvest interval)."""
    if waiting_days is None:
        return None
    return spray_date + timedelta(days=int(waiting_days))
