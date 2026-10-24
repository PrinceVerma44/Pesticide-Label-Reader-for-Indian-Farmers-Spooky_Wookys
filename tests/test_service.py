from datetime import date

import pytest

from backend import service

LABEL = {
    "product_name": "Test Spray",
    "toxicity_color": "yellow",
    "pesticide_type": "insecticide",
    "application_method": "foliar spray",
    "pre_harvest_interval_days": 7,
    "uses": [{"crop": "cotton", "pest": "aphid", "dose_unit": "ml", "dose_per_litre": 2.5}],
    "safety_steps": ["Wear gloves"],
}


def test_analyze_happy_path():
    result, facts = service.analyze(LABEL, 0, 16, date(2026, 10, 24), "black")
    assert result["tank_dose"]["amount"] == 40.0
    assert result["earliest_harvest_date"] == "2026-10-31"
    assert result["soil"]["name"].startswith("Black cotton")
    assert facts["amount_per_tank"] == "40.0 ml"


def test_analyze_without_use_index_still_gives_soil_and_harvest():
    result, _ = service.analyze(LABEL, None, 16, date(2026, 10, 24), "sandy")
    assert result["tank_dose"] is None and result["soil_cautions"]


def test_bad_soil():
    with pytest.raises(service.BadInput):
        service.analyze(LABEL, 0, 16, None, "moon-dust")


def test_bad_use_index():
    with pytest.raises(service.BadInput):
        service.analyze(LABEL, 5, 16, None, "red")


def test_malformed_label_is_bad_input():
    bad = {**LABEL, "uses": [{"dose_unit": "ml", "dose_per_litre": "lots"}]}
    with pytest.raises(service.BadInput):
        service.analyze(bad, 0, 16, None, "red")


def test_language_check():
    service.check_language("Hindi")
    with pytest.raises(service.BadInput):
        service.check_language("Klingon")


def test_product_lookup_shape():
    info = service.product_lookup("cotton", "", "clay")
    assert set(info) == {"matches", "list_empty", "soil", "soil_cautions"}
