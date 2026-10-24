import logging
import os
from datetime import date
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from kisanlabel.explain import LANGUAGES, explain, explain_recommendation
from kisanlabel.extract import extract_label
from kisanlabel.soil import SOILS, soil_cautions

from . import service
from .ratelimit import RateLimiter

log = logging.getLogger("kisanlabel")

app = FastAPI(
    title="KisanLabel API",
    version="0.1.0",
    description="Read pesticide labels with Gemma 4, work out tank doses, add soil cautions, explain in local languages.",
)


origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


limiter = RateLimiter(limit=int(os.getenv("RATE_LIMIT_PER_MIN", "20")))

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp"}


class AnalyzeRequest(BaseModel):
    label: dict[str, Any] = Field(description="The JSON returned by /api/label/read")
    use_index: Optional[int] = Field(None, description="Which row of label.uses the farmer picked")
    tank_litres: float = Field(16, gt=0, le=200)
    spray_date: Optional[date] = Field(None, description="Defaults to today")
    soil: str = Field("alluvial", description="One of /api/meta soils")


class ExplainRequest(AnalyzeRequest):
    language: str = Field("English", description="One of the language names from /api/meta")


class ProductExplainRequest(BaseModel):
    crop: str = ""
    pest: str = ""
    soil: str = "alluvial"
    language: str = "English"


def _bad_input(e: service.BadInput):
    return HTTPException(422, str(e))


def _call_model(fn, *args):
    try:
        return fn(*args)
    except RuntimeError as e:
        log.error("Server config problem: %s", e)
        raise HTTPException(503, str(e))
    except ValueError:
        raise HTTPException(502, "Could not understand the model's reply. Try a clearer photo.")
    except Exception:
        log.exception("Model call failed")
        raise HTTPException(502, "The AI service failed. Please try again.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return {"languages": LANGUAGES, "soils": SOILS, "default_tank_litres": 16}


@app.post("/api/label/read", dependencies=[Depends(limiter)])
def read_label(image: UploadFile = File(...)):
    if image.content_type not in ALLOWED_IMAGES:
        raise HTTPException(415, "Upload a JPEG, PNG or WebP image.")
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(400, "Empty file.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image is larger than 8 MB.")
    return _call_model(extract_label, data, image.content_type)


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        result, _ = service.analyze(req.label, req.use_index, req.tank_litres, req.spray_date, req.soil)
    except service.BadInput as e:
        raise _bad_input(e)
    return result


@app.post("/api/explain", dependencies=[Depends(limiter)])
def explain_label(req: ExplainRequest):
    try:
        service.check_language(req.language)
        _, facts = service.analyze(req.label, req.use_index, req.tank_litres, req.spray_date, req.soil)
    except service.BadInput as e:
        raise _bad_input(e)
    text = _call_model(explain, facts, req.language)
    return {"language": req.language, "explanation": text}


@app.get("/api/products")
def products(crop: str = "", pest: str = "", soil: str = "alluvial"):
    try:
        return service.product_lookup(crop, pest, soil)
    except service.BadInput as e:
        raise _bad_input(e)


@app.post("/api/products/explain", dependencies=[Depends(limiter)])
def explain_products(req: ProductExplainRequest):
    try:
        service.check_language(req.language)
        info = service.product_lookup(req.crop, req.pest, req.soil)
    except service.BadInput as e:
        raise _bad_input(e)
    text = _call_model(
        explain_recommendation, req.crop, req.pest, info["soil"]["name"],
        info["matches"][:5], info["soil_cautions"], req.language,
    )
    return {"language": req.language, "explanation": text}
