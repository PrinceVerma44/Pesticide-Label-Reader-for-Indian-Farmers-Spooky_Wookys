"""Locale files stay valid and lookups fall back to English."""

from kisanlabel.i18n import LANGUAGE_CODES, _load, soil_name, translate
from kisanlabel.soil import SOILS


def test_every_locale_file_parses_with_both_sections():
    for code in LANGUAGE_CODES.values():
        data = _load(code)
        assert set(data) == {"ui", "soils"}, code
        assert set(data["soils"]) == set(SOILS), code


def test_translate_falls_back_to_english():
    assert translate("No such string", "Hindi") == "No such string"
    assert translate("Mix in one", "English") == "Mix in one"
    assert translate("Mix in one", "Klingon") == "Mix in one"


def test_known_translations_resolve():
    assert translate("Mix in one", "Hindi") == "एक में मिलाएँ"
    assert translate("Wear gloves", "Tamil") == "கையுறைகள் அணியுங்கள்"


def test_soil_names_resolve_and_fall_back():
    assert soil_name("sandy", "Hindi") == "रेतीली / हल्की मिट्टी"
    assert soil_name("black", "Marathi") == "काळी कापूस माती"
    assert soil_name("clay", "English") == SOILS["clay"]
