from kisanlabel.recommend import find_products
from kisanlabel.soil import SOILS, soil_cautions

PRODUCTS = [
    {"crop": "Cotton", "pest": "Aphid", "product_name": "TestProd A"},
    {"crop": "Tomato", "pest": "Early blight", "product_name": "TestProd B"},
]


def test_every_soil_has_cautions():
    for key in SOILS:
        assert soil_cautions(key)


def test_soil_acting_product_gets_extra_note():
    base = soil_cautions("sandy")
    assert len(soil_cautions("sandy", application_method="soil application")) == len(base) + 1
    assert len(soil_cautions("sandy", pesticide_type="herbicide")) == len(base) + 1


def test_foliar_note():
    assert any("leaves" in n for n in soil_cautions("black", application_method="foliar spray"))


def test_find_products_matches_crop_and_pest():
    assert [p["product_name"] for p in find_products("cotton", "", PRODUCTS)] == ["TestProd A"]
    assert find_products("tomato", "blight", PRODUCTS)[0]["product_name"] == "TestProd B"
    assert find_products("rice", "", PRODUCTS) == []
    assert len(find_products("", "", PRODUCTS)) == 2
