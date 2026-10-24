import pytest
from fastapi.testclient import TestClient

from backend import main

client = TestClient(main.app)

LABEL = {
    "product_name": "Test Spray",
    "pre_harvest_interval_days": 7,
    "uses": [{"crop": "cotton", "dose_unit": "ml", "dose_per_litre": 2.5}],
}


def test_health_and_meta():
    assert client.get("/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert "black" in meta["soils"] and "Hindi" in meta["languages"].values()


def test_analyze():
    r = client.post("/api/analyze", json={"label": LABEL, "use_index": 0, "tank_litres": 16, "soil": "black"})
    assert r.status_code == 200 and r.json()["tank_dose"]["amount"] == 40.0


def test_analyze_rejects_bad_soil_and_tank():
    assert client.post("/api/analyze", json={"label": LABEL, "soil": "nope"}).status_code == 422
    assert client.post("/api/analyze", json={"label": LABEL, "tank_litres": 0}).status_code == 422


def test_read_label_rejects_non_image():
    r = client.post("/api/label/read", files={"image": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_read_label_with_fake_model(monkeypatch):
    monkeypatch.setattr(main, "extract_label", lambda data, mime: {"product_name": "Fake", "uses": []})
    r = client.post("/api/label/read", files={"image": ("l.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert r.status_code == 200 and r.json()["product_name"] == "Fake"


def test_explain_with_fake_model(monkeypatch):
    monkeypatch.setattr(main, "explain", lambda facts, lang: f"[{lang}] ok")
    r = client.post("/api/explain", json={"label": LABEL, "use_index": 0, "language": "Marathi"})
    assert r.status_code == 200 and r.json()["explanation"] == "[Marathi] ok"


def test_explain_rejects_unknown_language():
    r = client.post("/api/explain", json={"label": LABEL, "language": "Klingon"})
    assert r.status_code == 422


def test_products_endpoint():
    r = client.get("/api/products", params={"crop": "cotton", "soil": "clay"})
    assert r.status_code == 200 and "soil_cautions" in r.json()
