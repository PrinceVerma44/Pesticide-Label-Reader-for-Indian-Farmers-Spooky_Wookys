import json
import re


def parse_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (handles ```json fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", text or "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Model reply did not contain a JSON object.")
    return json.loads(text[start : end + 1])
