from .client import MODEL, get_client
from .jsonparse import parse_json

EXTRACT_PROMPT = """You are reading a photo of a pesticide label sold in India.
Extract ONLY what is printed on the label. Never guess. If something is not visible or not
readable, use null and add its name to "unreadable_or_missing".

Return ONLY one JSON object, no other text, in exactly this shape:
{
  "product_name": string|null,
  "active_ingredient": string|null,
  "formulation": string|null,
  "pesticide_type": "insecticide"|"fungicide"|"herbicide"|"other"|null,
  "application_method": "foliar spray"|"soil application"|"seed treatment"|"other"|null,
  "toxicity_color": "red"|"yellow"|"blue"|"green"|null,
  "uses": [
    {
      "crop": string,
      "pest": string|null,
      "dose_unit": "ml"|"g"|null,
      "dose_per_litre": number|null,
      "dose_per_acre": number|null,
      "water_per_acre_litres": number|null
    }
  ],
  "pre_harvest_interval_days": number|null,
  "safety_steps": [string],
  "first_aid": [string],
  "unreadable_or_missing": [string]
}
Rules:
- Convert doses to ml or g (e.g. 1 kg -> 1000 g, 1 litre -> 1000 ml).
- toxicity_color is the colour of the triangle/square at the bottom of the label.
- pre_harvest_interval_days is the waiting period between last spray and harvest.
- The label may be in English, Hindi or another Indian language. Keep safety text short.
"""


def extract_label(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Send the label photo to Gemma 4 and get structured data back."""
    from google.genai import types

    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), EXTRACT_PROMPT],
    )
    data = parse_json(response.text)
    data.setdefault("uses", [])
    data.setdefault("safety_steps", [])
    data.setdefault("first_aid", [])
    data.setdefault("unreadable_or_missing", [])
    return data
