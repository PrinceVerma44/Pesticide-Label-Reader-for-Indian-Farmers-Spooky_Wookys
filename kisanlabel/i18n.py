"""UI translations, loaded from JSON locale files in locales/.

Each file is named by language code (hi, mr, gu, ta, te, kn, bn, pa) and
has two sections:
  "ui":    English string -> translation (headings, labels, cautions)
  "soils": SOILS key (sandy, red, ...) -> translated soil name

English needs no file: it is the key language, so lookups fall back to
the English string itself. Missing keys also fall back to English, so a
half-finished locale file can never break the UI.
"""
import json
from functools import lru_cache
from pathlib import Path

from .soil import SOILS

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

LANGUAGE_CODES = {
    "Hindi": "hi",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Bengali": "bn",
    "Punjabi": "pa",
}


@lru_cache(maxsize=None)
def _load(code):
    path = LOCALES_DIR / f"{code}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def translate(text, language_value):
    """Translate an English UI string; falls back to the English string."""
    code = LANGUAGE_CODES.get(language_value)
    if not code:
        return text
    return _load(code).get("ui", {}).get(text, text)


def soil_name(soil_key, language_value):
    """Translated soil name for a SOILS key; falls back to the English name."""
    code = LANGUAGE_CODES.get(language_value)
    if code:
        name = _load(code).get("soils", {}).get(soil_key)
        if name:
            return name
    return SOILS[soil_key]
