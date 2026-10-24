import json

from .client import MODEL, get_client

HELPLINE = "Kisan Call Centre 1800-180-1551"

LANGUAGES = {
    "English": "English",
    "हिन्दी": "Hindi",
    "मराठी": "Marathi",
    "ગુજરાતી": "Gujarati",
    "தமிழ்": "Tamil",
    "తెలుగు": "Telugu",
    "ಕನ್ನಡ": "Kannada",
    "বাংলা": "Bengali",
    "ਪੰਜਾਬੀ": "Punjabi",
}

EXPLAIN_PROMPT = """You are helping a small farmer in India who cannot read long text.
Below are FACTS taken from a pesticide label, plus numbers already calculated for the
farmer's tank and cautions for the farmer's soil. Use ONLY these facts. Do NOT add any
number, chemical, crop, or advice that is not in the facts. If a fact is null or missing,
say it is not on the label and tell the farmer to ask the agri-input shop or call {helpline}.

Write in {language}. Short sentences, simple everyday words, about 150 words, in this order:
1. How much to mix in one tank.
2. When it is safe to harvest.
3. Safety steps and first aid.
4. Soil cautions.
End with: "Always read the label on the bottle too."

FACTS:
{facts}
"""

RECOMMEND_PROMPT = """You are helping a farmer in India choose a pesticide.
The CANDIDATES below are the ONLY products you may mention. Never name any other product.
If the list is empty, say no verified product was found and tell the farmer to ask the local
agriculture officer or call {helpline}. Mention the soil cautions. Tell the farmer to confirm
with the agriculture officer or Krishi Vigyan Kendra before buying, and to read the label.

Write in {language}. Short sentences, simple words, about 120 words.

CROP: {crop}
PEST: {pest}
SOIL: {soil}
CANDIDATES: {candidates}
SOIL CAUTIONS: {cautions}
"""


def build_facts(label, use, tank_dose, acres, harvest_date, tank_litres, soil_name=None, soil_notes=None):
    return {
        "product_name": label.get("product_name"),
        "toxicity_color": label.get("toxicity_color"),
        "crop": use.get("crop") if use else None,
        "pest": use.get("pest") if use else None,
        "tank_size_litres": tank_litres,
        "amount_per_tank": f"{tank_dose.amount} {tank_dose.unit}" if tank_dose else None,
        "acres_covered_per_tank": acres,
        "waiting_period_days": label.get("pre_harvest_interval_days"),
        "earliest_harvest_date": harvest_date.isoformat() if harvest_date else None,
        "safety_steps": label.get("safety_steps") or None,
        "first_aid": label.get("first_aid") or None,
        "soil_type": soil_name,
        "soil_cautions": soil_notes or None,
    }


def _ask(prompt):
    return get_client().models.generate_content(model=MODEL, contents=prompt).text


def explain(facts: dict, language_name: str) -> str:
    return _ask(
        EXPLAIN_PROMPT.format(
            helpline=HELPLINE, language=language_name, facts=json.dumps(facts, ensure_ascii=False, indent=2)
        )
    )


def explain_recommendation(crop, pest, soil_name, candidates, cautions, language_name):
    return _ask(
        RECOMMEND_PROMPT.format(
            helpline=HELPLINE,
            language=language_name,
            crop=crop or "not given",
            pest=pest or "not given",
            soil=soil_name,
            candidates=json.dumps(candidates, ensure_ascii=False),
            cautions=json.dumps(cautions, ensure_ascii=False),
        )
    )
