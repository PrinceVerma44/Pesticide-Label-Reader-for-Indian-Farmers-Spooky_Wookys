import datetime as dt

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from kisanlabel.dose import acres_per_tank, dose_for_tank, safe_harvest_date
from kisanlabel.i18n import soil_name as _soil_name, translate
from kisanlabel.explain import HELPLINE, LANGUAGES, build_facts, explain, explain_recommendation
from kisanlabel.extract import extract_label
from kisanlabel.recommend import find_products, load_products
from kisanlabel.soil import SOILS, soil_cautions
from kisanlabel.toxicity import describe


DEMO_LABEL = {
    "product_name": "Sample Label (DEMO)",
    "active_ingredient": "Demo active ingredient",
    "formulation": "Demo formulation",
    "pesticide_type": "insecticide",
    "application_method": "foliar spray",
    "toxicity_color": "yellow",
    "uses": [
        {"crop": "Tomato", "pest": "Aphid", "dose_unit": "ml",
         "dose_per_litre": 2.5, "dose_per_acre": None, "water_per_acre_litres": 200},
        {"crop": "Cotton", "pest": "Bollworm", "dose_unit": "ml",
         "dose_per_litre": 2.0, "dose_per_acre": None, "water_per_acre_litres": 200},
    ],
    "pre_harvest_interval_days": 7,
    "safety_steps": ["Wear gloves, mask and long sleeves", "Do not eat, drink or smoke while spraying"],
    "first_aid": ["If on skin, wash with plenty of soap and water", "If swallowed, call a doctor at once"],
    "unreadable_or_missing": [],
}

TOXICITY_CSS = {
    "red": ("#C62828", "#FFEBEE"),
    "yellow": ("#F9A825", "#FFFDE7"),
    "blue": ("#1565C0", "#E3F2FD"),
    "green": ("#2E7D32", "#E8F5E9"),
}


def pick(label, options, key, default=None):
    fallback = default or options[0]
    if hasattr(st, "segmented_control"):
        result = st.segmented_control(label, options, key=key, default=fallback)
        return result if result is not None else fallback
    return st.selectbox(label, options, key=key)


def tr(language_value, en, hi=None, mr=None):
    out = translate(en, language_value)
    if out != en:
        return out
    if language_value == "Hindi" and hi:
        return hi
    if language_value == "Marathi" and mr:
        return mr
    return en


def tr_known(text, language_value):
    return translate(text, language_value)


def us(key, language_value):
    return translate(key, language_value)


def soil_display(soil_key, language_value):
    return _soil_name(soil_key, language_value)


st.set_page_config(page_title="KisanLabel 🌾", page_icon="🌾", layout="centered")
st.markdown("""
<style>
  /* Beauty pass only: no logic, widget names, or text changed below.
     Same classes as the proven ui.py, just richer styling. */
  .main { max-width: 820px; }
  html, body { font-size: 18px; font-family: 'Inter', system-ui, sans-serif; }
  .stApp {
    background-color: #FFF9EC;
    background-image: radial-gradient(#EBDDC0 1.2px, transparent 1.2px);
    background-size: 24px 24px;
  }
  #MainMenu, footer { visibility: hidden; }
  h1 { font-size: 2.4rem !important; line-height: 1.05; font-family: 'Baloo 2', system-ui, sans-serif; }
  h2, h3 { margin-top: 1.3rem !important; color: #1B5E20; font-family: 'Baloo 2', system-ui, sans-serif; }
  h3 { border-bottom: 3px solid #FFD54F; padding-bottom: 0.25rem; }
  .stButton > button {
    width: 100%; background: linear-gradient(135deg, #1B5E20, #2E7D32); color: #fff; border: none;
    font-size: 1.15rem; font-weight: 800; padding: 0.95rem 1rem; border-radius: 18px;
    box-shadow: 0 8px 20px rgba(27, 94, 32, 0.28);
  }
  .stButton > button:hover { background: linear-gradient(135deg, #2E7D32, #43A047); color: #fff; transform: translateY(-1px); }
  .stButton > button:active { transform: translateY(0px); box-shadow: 0 4px 10px rgba(27, 94, 32, 0.28); }
  .hero {
    background: linear-gradient(135deg, #E8F5E9, #FFF3C4);
    border: 2px solid #D4A017; border-left: 10px solid #FF9933; border-radius: 24px;
    padding: 1.3rem 1.5rem; box-shadow: 0 12px 30px rgba(27, 94, 32, 0.14);
  }
  .banner { margin: 0.2rem 0 0.2rem 0; border-radius: 24px; overflow: hidden;
    border: 2px solid #D4A017; box-shadow: 0 12px 30px rgba(27, 94, 32, 0.16); }
  .banner svg { width: 100% !important; height: auto !important; display: block; }
  .hero p { margin: 0.25rem 0; color: #263238; }
  .label-card {
    background: #FFFFFF; border: 2px solid #D4A017; border-left: 8px solid #1B5E20; border-radius: 22px;
    padding: 1.3rem 1.5rem; margin: 1rem 0; box-shadow: 0 12px 30px rgba(38, 50, 56, 0.12);
  }
  .dose-hero {
    background: linear-gradient(135deg, #123F16, #1B5E20 55%, #2E7D32); color: #fff; border-radius: 24px;
    padding: 1.6rem; text-align: center; margin: 1.1rem 0; border: 2px solid #FFD54F;
    box-shadow: 0 16px 34px rgba(27, 94, 32, 0.32);
  }
  .dose-hero .big { font-size: 3.1rem; font-weight: 900; line-height: 1; font-family: 'Baloo 2', system-ui, sans-serif; }
  .dose-hero .small { opacity: 0.95; margin-top: 0.45rem; }
  .timeline { display: flex; gap: 0.6rem; text-align: center; }
  .timeline > div {
    flex: 1; background: #FFFFFF; border-top: 5px solid #FF9933; border-radius: 16px;
    padding: 0.9rem 0.4rem; box-shadow: 0 8px 20px rgba(38, 50, 56, 0.10);
  }
  .timeline b { display: block; font-size: 1.05rem; }
  .stepbar {
    display: inline-block; background: #1B5E20; color: #fff; font-weight: 800;
    letter-spacing: 0.02em; padding: 0.45rem 1rem; border-radius: 999px; margin-top: 0.8rem;
    box-shadow: 0 6px 16px rgba(27, 94, 32, 0.25);
  }
</style>
""", unsafe_allow_html=True)


label = st.session_state.get("label")
step = 3 if label else (2 if st.session_state.get("photo_done") else 1)


try:
    import base64 as _base64
    from pathlib import Path as _Path

    _banner_path = _Path(__file__).parent / "banner.svg"
    _banner_b64 = _base64.b64encode(_banner_path.read_bytes()).decode("ascii")
    st.markdown(
        f'<div class="banner"><img src="data:image/svg+xml;base64,{_banner_b64}" '
        'style="width:100%;height:auto;display:block;" /></div>',
        unsafe_allow_html=True,
    )
except Exception:
    st.markdown("""
<div class="hero">
  <h1>🌾 KisanLabel</h1>
  <p><b>Photo of a label → dose for <i>your</i> tank, in <i>your</i> language.</b></p>
  <p>For farmers, farm workers and shop staff. No guessing — if it is not on the label, we say so.</p>
</div>
""", unsafe_allow_html=True)
st.markdown(f"""
<p class="stepbar">{'✅' if step > 1 else '①'} Photo &nbsp;→&nbsp; {'✅' if step > 2 else '②'} Your field &nbsp;→&nbsp; {'✅' if step > 2 else '③'} Result card</p>
""", unsafe_allow_html=True)

mode = pick("What do you want to do?", ["📷 Scan a label", "🔎 Find a product"], key="mode")


st.markdown("### 🌾 Your field")
col_a, col_b = st.columns(2)
with col_a:
    lang_label = pick("Language", list(LANGUAGES), key="lang")
with col_b:
    soil_key = st.selectbox("Soil type", list(SOILS), format_func=SOILS.get, key="soil")
language = LANGUAGES.get(lang_label, "English")
soil_name = SOILS[soil_key]
tank = st.slider("Sprayer tank size (litres) — drag it, the dose updates live",
                 min_value=5, max_value=25, value=16, step=1, key="tank")
spray_date = st.date_input("Spray date", dt.date.today(), key="spray_date")
st.caption("💡 Dragging the tank slider does not call the AI again. The dose is recalculated in Python. Changing language changes the headings below — tap 'Explain' again to re-translate the paragraph.")


if mode == "📷 Scan a label":
    st.markdown("### ① Photo of the label")
    up_col, cam_col = st.columns(2)
    with up_col:
        uploaded = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png", "webp"], key="up")
    with cam_col:
        try:
            camera = st.camera_input("Or take a photo", key="cam")
        except Exception:
            camera = None
    photo = uploaded or camera
    if photo:
        st.session_state["photo_done"] = True
        st.image(photo, caption="Your label photo", use_container_width=True)

    btn_col, demo_col = st.columns(2)
    with btn_col:
        read_clicked = st.button("📷 Read this label", type="primary")
    with demo_col:
        demo_clicked = st.button("✨ Try a demo label (no photo needed)")

    if demo_clicked:
        st.session_state["label"] = DEMO_LABEL
        st.session_state["demo"] = True
        st.rerun()
    if read_clicked and photo:
        with st.spinner("Gemma is reading the label…"):
            try:
                st.session_state["label"] = extract_label(photo.getvalue(), photo.type or "image/jpeg")
                st.session_state["demo"] = False
            except Exception as e:
                st.session_state["label"] = None
                st.error(f"Could not read the label: {e}")
    elif read_clicked:
        st.warning("First upload or take a photo — or tap 'Try a demo label'.")

    label = st.session_state.get("label")
    if not label:
        st.info("👆 Upload a label photo above, then tap Read. Judges: the demo button works with no API key.")
        st.stop()

    if st.session_state.get("demo"):
        st.warning("⚠️ DEMO LABEL — for showing the UI only. Not real advice, not a real product.")


    tox_bg, tox_fg = TOXICITY_CSS.get(label.get("toxicity_color"), ("#37474F", "#ECEFF1"))
    st.markdown(f"""
    <div class="label-card">
      <div style="font-size:0.85rem; letter-spacing:0.12em; color:#1B5E20; font-weight:800;">KISANLABEL · READ FROM THE PHOTO</div>
      <h2 style="margin:0.2rem 0;">{label.get("product_name") or "Unknown product"}</h2>
      <p style="margin:0;">{label.get("active_ingredient") or ""}</p>
      <p style="background:{tox_fg}; border-left:6px solid {tox_bg}; padding:0.5rem 0.8rem; border-radius:8px; margin-top:0.8rem;">
        <b>{describe(label.get("toxicity_color"))}</b></p>
    </div>
    """, unsafe_allow_html=True)

    uses = label.get("uses") or []
    use = None
    if uses:
        names = [f"{u.get('crop')} — {u.get('pest') or 'any pest'}" for u in uses]
        use = uses[st.selectbox("Your crop / pest (from the label)", range(len(uses)),
                                format_func=lambda i: names[i], key="use")]

    tank_dose = dose_for_tank(use, tank) if use else None
    acres = acres_per_tank(use, tank) if use else None
    harvest = safe_harvest_date(spray_date, label.get("pre_harvest_interval_days"))
    notes = soil_cautions(soil_key, label.get("pesticide_type"), label.get("application_method"))

    st.markdown(f"### ② {tr(language, 'Your dose — live', 'आपकी खुराक — लाइव', 'तुमचा डोस — थेट')}")
    if tank_dose:
        st.markdown(f"""
        <div class="dose-hero">
          <div style="font-size:1rem; opacity:0.9;">{us("Mix in one", language)} {tank:g} L {us("tank", language)}</div>
          <div class="big">{tank_dose.amount} {tank_dose.unit}</div>
          <div class="small">{us("Working", language)}: {tank_dose.how} &nbsp;·&nbsp; {us("One tank covers about", language)} {acres} {us("acre", language)}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"Dose not clear on the label. Do not guess — ask the shop or call {HELPLINE}.")

    st.markdown(f"### ③ {tr(language, 'When can you harvest?', 'कटाई कब कर सकते हैं?', 'कापणी कधी करू शकता?')}")
    if harvest:
        st.markdown(f"""
        <div class="timeline">
          <div>🌱<b>{us("Spray", language)}</b>{spray_date.strftime("%d %b %Y")}</div>
          <div>⏳<b>{us("Wait", language)}</b>{label['pre_harvest_interval_days']} {us("days", language)}</div>
          <div>🌾<b>{us("Harvest from", language)}</b>{harvest.strftime("%d %b %Y")}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(us("Waiting period not found on the label.", language))

    st.markdown(f"### 🪱 {tr(language, 'Cautions for', 'सावधानियाँ', 'काळजी')} {soil_display(soil_key, language)}")
    for n in notes:
        st.write("• " + tr_known(n, language))


    _unreadable = [x for x in (label.get("unreadable_or_missing") or []) if isinstance(x, str) and x.strip()]
    if _unreadable:
        st.warning("Could not read: " + ", ".join(_unreadable) + ". Retake in better light.")


    st.markdown(f"### 🧤 {tr(language, 'Safety check — tick before you spray', 'सुरक्षा जाँच — छिड़काव से पहले टिक करें', 'सुरक्षा तपासणी — फवारणीपूर्वी टिक करा')}")
    _safety = [x for x in (label.get("safety_steps") or []) if isinstance(x, str) and x.strip()]
    ppe_items = list(dict.fromkeys(_safety + [
        "Wear gloves", "Wear a mask", "Wear long sleeves", "Wear goggles", "Wash hands after spraying"]))


    ticks = [st.checkbox(tr_known(item, language), key=f"ppe_{i}") for i, item in enumerate(ppe_items)]
    st.caption(us("Label wording stays as printed so you can check it against the bottle — the Explain paragraph below translates it in full.", language))
    done = sum(ticks)
    st.progress(done / max(len(ticks), 1), text=f"{us('Safety ready', language)}: {done}/{len(ticks)} {us('ticked', language)}")
    if done == len(ticks):
        st.success("✅ " + us("All safety steps ticked. Still follow the printed label.", language))
    _first_aid = label.get("first_aid") or []
    if isinstance(_first_aid, str):
        _first_aid = [_first_aid]
    _first_aid = [f for f in _first_aid if isinstance(f, str) and f.strip()]
    if _first_aid:
        with st.expander("🩹 " + us("First aid (from the label)", language)):
            for f in _first_aid:
                st.write("• " + f)


    if st.button(f"🗣️ {us('Explain', language)} {lang_label}"):
        with st.spinner("Writing a simple explanation…"):
            try:
                facts = build_facts(label, use, tank_dose, acres, harvest, tank, soil_name, notes)


                st.session_state["explanation"] = explain(facts, language)
                st.session_state["explanation_lang"] = language
            except Exception as e:


                st.error(f"Could not write the explanation: {e}")
                st.info("Fix: make sure Ollama is running and gemma3:4b is pulled (ollama pull gemma3:4b), then restart Streamlit. No API key is used.")
    if st.session_state.get("explanation"):
        if st.session_state.get("explanation_lang") != language:
            st.info(f"Language changed to {lang_label}. Tap 'Explain in {lang_label}' again to translate this result.")
        st.markdown(st.session_state["explanation"])
    with st.expander("🔍 " + us("Raw data read from the label (for judges)", language)):
        st.json(label)


else:
    st.markdown("### 🔎 Find a product")
    st.write("Suggestions come **only** from the verified list — the AI never invents a product.")
    crop_in = st.text_input("Crop (e.g. cotton, tomato)", key="crop")
    pest_in = st.text_input("Pest or disease (e.g. aphid, blight)", key="pest")
    if st.button("Find products", type="primary"):
        products = load_products()
        if not products:
            st.warning("The verified list (data/registered_products.csv) is empty. Fill it from CIB&RC / agriculture university sources.")
        matches = find_products(crop_in, pest_in, products)
        cautions = soil_cautions(soil_key)
        if matches:
            for p in matches:
                st.markdown(f"""
                <div class="label-card">
                  <b style="font-size:1.2rem;">{p.get("product_name", "")}</b><br>
                  {p.get("active_ingredient", "")} · {p.get("pesticide_type", "")} · {p.get("application_method", "")}<br>
                  <span style="color:#555;">Crop: {p.get("crop", "")} · Pest: {p.get("pest", "")}</span>
                </div>
                """, unsafe_allow_html=True)
        elif products:
            st.info(f"No verified product found. Ask the local agriculture officer or call {HELPLINE}.")
        st.markdown(f"**Cautions for {soil_name}**")
        for n in cautions:
            st.write("• " + tr_known(n, language))
        if products:
            with st.spinner("Writing explanation…"):
                try:
                    st.markdown(explain_recommendation(crop_in, pest_in, soil_name, matches[:5], cautions, language))
                except Exception as e:
                    st.error(f"Could not write the explanation: {e}")
                    st.info("Fix: make sure Ollama is running and gemma3:4b is pulled (ollama pull gemma3:4b), then restart Streamlit. No API key is used.")

st.divider()
st.caption(f"{us('Always check the printed label.', language)} {us('Unsure? Call', language)} {HELPLINE} {us('or ask your local agriculture officer / Krishi Vigyan Kendra.', language)}")
