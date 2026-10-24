# 🌾 KisanLabel: Pesticide Label Reader for Indian Farmers

Built at **Hacktoberfest 26 Hack Day** (NST.ADYPU · NSTSDC, Pune) for Problem Statement #5.

Pesticide labels are dense and often in English or mixed languages😵‍💫. Wrong use causes illness🤒,
crop damage‼️ and wasted money. KisanLabel lets a farmer **take a photo of the label** and get:

- the **right dose for their own tank** (e.g. 16 L knapsack sprayer)
- the **waiting period** and the **earliest safe harvest date📅🟢**
- **safety steps and first aid⛑️**, explained in **their own language**
- **⚠️cautions for their soil type** (sandy, red, black cotton, alluvial, laterite, clay)
- a **Find a product** tab that suggests products for a crop + pest from a verified list☑️

## How it works🛠️

```
Label photo ──► Gemma 4 (vision) ──► structured JSON ──► Python maths ──► Gemma 4 (writing) ──► simple explanation
                 reads the label      dose, wait days,     tank dose,        uses ONLY the         in Hindi, Marathi,
                 (no guessing)        safety, colour       harvest date      checked facts         Tamil, etc.
```

1. **Read** (`kisanlabel/extract.py`): Gemma 4 looks at the photo and returns JSON. Anything it
   cannot read is `null` and listed under `unreadable_or_missing`. It is told never to guess.
2. **Calculate** (`kisanlabel/dose.py`): dose per tank, acres covered and harvest date are
   computed in plain Python, not by the model. The working is shown so it can be checked.
3. **Explain** (`kisanlabel/explain.py`): Gemma 4 turns the verified facts into short, simple
   text in the chosen language. It is told to use only those facts and to point to the
   Kisan Call Centre (1800-180-1551) when something is missing.
4. **UI** (`app.py`): Streamlit app with upload/camera, language and tank-size selectors.
5. **API** (`backend/`): FastAPI endpoints wrapping the same modules (see below).

**Why this design?** A wrong number on a pesticide can hurt someone. So the LLM only *reads*
and *explains*; arithmetic and dates are deterministic and unit-tested.

## Soil and product recommendations💭 (how it's kept safe)

Which pesticide to use depends mainly on the **crop and pest/disease🦠**, not on soil. Soil changes
how a chemical behaves (washes into groundwater, sticks, lasts) and how a soil-applied product
should be dosed. So:

- `kisanlabel/soil.py` gives **soil-specific cautions⚠️** (e.g. leaching on sandy soil, cracks in black cotton soil).
- `kisanlabel/recommend.py` suggests products **only from `data/registered_products.csv`**, a list the
  team fills from CIB&RC and agriculture-university sources✅. The AI never invents a product.
- The app always tells users to confirm with the agriculture officer👮 / KVK and read the printed label.

## Backend API (FastAPI)⚙️

`backend/` exposes the same logic as a REST API so any web frontend (React, plain JS, mobile) can use it.
Start it with `uvicorn backend.main:app --reload --port 8000`, then open **http://localhost:8000/docs**
for interactive docs.

| Method | Path | What it does | Calls Gemma? |
|---|---|---|---|
| GET | `/health` | Is the server up | no |
| GET | `/api/meta` | Languages, soil types, default tank size | no |
| POST | `/api/label/read` | Label photo (multipart `image`) → structured JSON | yes |
| POST | `/api/analyze` | JSON → tank dose, harvest date, soil cautions | no |
| POST | `/api/explain` | Same input + `language` → simple explanation | yes |
| GET | `/api/products?crop=&pest=&soil=` | Verified products + soil cautions | no |
| POST | `/api/products/explain` | Explain product suggestions in a language | yes |

Typical frontend flow: `meta` → `label/read` (photo) → `analyze` (live as farmer changes tank/soil/crop)
→ `explain` (when they tap "Explain in Hindi").

```bash
curl -F "image=@samples/label.jpg" http://localhost:8000/api/label/read
curl -X POST http://localhost:8000/api/analyze -H "Content-Type: application/json" \
  -d '{"label": {"uses":[{"dose_unit":"ml","dose_per_litre":2.5}],"pre_harvest_interval_days":7}, "use_index":0, "tank_litres":16, "soil":"black"}'
```

Safety built in: image type and 8 MB size limits, per-IP rate limit on endpoints that call Gemma,
clean error messages, CORS controlled by `CORS_ORIGINS`, and the API key stays on the server.

## Run it🚀

```bash
git clone <your-repo-url> && cd kisanlabel
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then paste your GEMINI_API_KEY (free from Google AI Studio)
streamlit run app.py
pytest                      # runs the dose and parsing tests (no API key needed)
```

## Models, tools and licenses📦

| What | Use | License |
|---|---|---|
| Gemma 4 (`gemma-4-26b-a4b-it`, optionally `gemma-4-31b-it`) via the Gemini API | Reads label photo, writes explanation | See the Gemma 4 model card for its terms |
| CIB&RC / agri-university data (you add) | Verified product list | Check each source's terms |
| Streamlit | Web UI | Apache-2.0 |
| google-genai (Python SDK) | Calls the Gemini API | Apache-2.0 |
| python-dotenv | Loads `.env` | BSD-3-Clause |
| pytest | Tests | MIT |
| This project | | MIT (see `LICENSE`) |

## AI tools used while building⛏️

Parts of this scaffold were drafted with an AI assistant (Claude). The team reviewed and
understands the code and can explain every module.

## Limits and safety⚪️

- It is a **helper, not a replacement for the printed label** or an agriculture officer.
- Photo quality matters: glare, folds and tiny print reduce accuracy. The app flags unreadable fields.
- Doses depend on crop and pest; the farmer must pick the right row from the label.
- Translations are generated by a model and should be checked by native speakers before real rollout.

## Ideas for next steps🌀

- Offline / on-device Gemma for villages with poor internet
- Voice input and read-aloud output
- Warn when two products are mixed that should not be
- Test set of real Indian labels with accuracte numbers
- 
