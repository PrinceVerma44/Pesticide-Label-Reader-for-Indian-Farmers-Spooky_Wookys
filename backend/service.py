from dataclasses import asdict
from datetime import date
from typing import Optional

from kisanlabel.dose import acres_per_tank, dose_for_tank, safe_harvest_date
from kisanlabel.explain import LANGUAGES, build_facts
from kisanlabel.recommend import find_products, load_products
from kisanlabel.soil import SOILS, soil_cautions
from kisanlabel.toxicity import describe


class BadInput(ValueError):
    pass


def check_soil(key: str) -> None:
    if key not in SOILS:
        raise BadInput(f"Unknown soil '{key}'. Use one of: {', '.join(SOILS)}")


def check_language(name: str) -> None:
    if name not in LANGUAGES.values():
        raise BadInput(f"Unsupported language '{name}'. Use one of: {', '.join(LANGUAGES.values())}")


def analyze(label: dict, use_index: Optional[int], tank_litres: float, spray_date: Optional[date], soil: str):
    check_soil(soil)
    uses = label.get("uses") or []
    use = None
    if use_index is not None:
        if not 0 <= use_index < len(uses):
            raise BadInput("use_index is out of range for this label.")
        use = uses[use_index]
    try:
        tank_dose = dose_for_tank(use, tank_litres) if use else None
        acres = acres_per_tank(use, tank_litres) if use else None
        harvest = safe_harvest_date(spray_date or date.today(), label.get("pre_harvest_interval_days"))
    except (TypeError, ValueError) as e:
        raise BadInput(f"The label data looks malformed: {e}")
    notes = soil_cautions(soil, label.get("pesticide_type"), label.get("application_method"))

    result = {
        "product_name": label.get("product_name"),
        "toxicity": describe(label.get("toxicity_color")),
        "tank_litres": tank_litres,
        "tank_dose": asdict(tank_dose) if tank_dose else None,
        "acres_per_tank": acres,
        "waiting_period_days": label.get("pre_harvest_interval_days"),
        "earliest_harvest_date": harvest.isoformat() if harvest else None,
        "soil": {"key": soil, "name": SOILS[soil]},
        "soil_cautions": notes,
        "unreadable_or_missing": label.get("unreadable_or_missing") or [],
    }
    facts = build_facts(label, use, tank_dose, acres, harvest, tank_litres, SOILS[soil], notes)
    return result, facts


def product_lookup(crop: str, pest: str, soil: str) -> dict:
    check_soil(soil)
    products = load_products()
    return {
        "matches": find_products(crop, pest, products),
        "list_empty": not products,
        "soil": {"key": soil, "name": SOILS[soil]},
        "soil_cautions": soil_cautions(soil),
    }
