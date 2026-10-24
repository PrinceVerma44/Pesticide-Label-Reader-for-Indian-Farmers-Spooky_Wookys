import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "registered_products.csv"


def load_products(path=DATA):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def find_products(crop, pest, products):
    crop, pest = (crop or "").strip().lower(), (pest or "").strip().lower()
    out = []
    for p in products:
        if crop and crop not in p.get("crop", "").lower():
            continue
        if pest and pest not in p.get("pest", "").lower():
            continue
        out.append(p)
    return out
