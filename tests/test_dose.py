from datetime import date

import pytest

from kisanlabel.dose import acres_per_tank, dose_for_tank, safe_harvest_date


def test_per_litre_dose():
    use = {"dose_unit": "ml", "dose_per_litre": 2.5}
    d = dose_for_tank(use, 16)
    assert (d.amount, d.unit) == (40.0, "ml")


def test_per_acre_dose_scales_with_water():
    use = {"dose_unit": "g", "dose_per_acre": 200, "water_per_acre_litres": 200}
    assert dose_for_tank(use, 16).amount == 16.0


def test_missing_data_returns_none():
    assert dose_for_tank({"dose_unit": "ml"}, 16) is None


def test_bad_tank_size():
    with pytest.raises(ValueError):
        dose_for_tank({"dose_unit": "ml", "dose_per_litre": 1}, 0)


def test_acres_per_tank():
    assert acres_per_tank({"water_per_acre_litres": 200}, 16) == 0.08
    assert acres_per_tank({}, 16) is None


def test_harvest_date():
    assert safe_harvest_date(date(2026, 10, 24), 7) == date(2026, 10, 31)
    assert safe_harvest_date(date(2026, 10, 24), None) is None
