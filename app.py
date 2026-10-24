import datetime as dt

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from kisanlabel.dose import acres_per_tank, dose_for_tank, safe_harvest_date
from kisanlabel.explain import HELPLINE, LANGUAGES, build_facts, explain, explain_recommendation
from kisanlabel.extract import extract_label
from kisanlabel.recommend import find_products, load_products
from kisanlabel.soil import SOILS, soil_cautions
from kisanlabel.toxicity import describe

st.set_page_config(page_title="KisanLabel", page_icon="🌾")
st.title("🌾 KisanLabel")
st.caption("Pesticide label help for farmers: dose for your tank, waiting period, soil cautions and safety, in your language.")

with st.sidebar:
    language_label = st.selectbox("Language", list(LANGUAGES))
    soil_key = st.selectbox("Your soil type", list(SOILS), format_func=SOILS.get)
    tank = st.number_input("Sprayer tank size (litres)", min_value=1.0, max_value=200.0, value=16.0, step=1.0)
    spray_date = st.date_input("Spray date", dt.date.today())

language = LANGUAGES[language_label]
soil_name = SOILS[soil_key]
scan_tab, find_tab = st.tabs(["📷 Scan a label", "🔎 Find a product"])

# ---------------------------------------------------------------- scan a label
with scan_tab:
    up_tab, cam_tab = st.tabs(["Upload photo", "Use camera"])
    with up_tab:
        uploaded = st.file_uploader("Label photo", type=["jpg", "jpeg", "png"])
    with cam_tab:
        camera = st.camera_input("Take a photo of the label")
    photo = uploaded or camera

    if photo and st.button("Read label", type="primary"):
        with st.spinner("Reading the label with Gemma 4..."):
            try:
                st.session_state.label = extract_label(photo.getvalue(), photo.type or "image/jpeg")
            except Exception as e:
                st.session_state.label = None
                st.error(f"Could not read the label: {e}")

    label = st.session_state.get("label")
    if label:
        st.subheader(label.get("product_name") or "Unknown product")
        st.write(describe(label.get("toxicity_color")))
        if label.get("active_ingredient"):
            st.write(f"**Active ingredient:** {label['active_ingredient']}")

        uses = label.get("uses") or []
        use = None
        if uses:
            names = [f"{u.get('crop')} - {u.get('pest') or 'any pest'}" for u in uses]
            use = uses[st.selectbox("Your crop / pest", range(len(uses)), format_func=lambda i: names[i])]

        tank_dose = dose_for_tank(use, tank) if use else None
        acres = acres_per_tank(use, tank) if use else None
        harvest = safe_harvest_date(spray_date, label.get("pre_harvest_interval_days"))
        notes = soil_cautions(soil_key, label.get("pesticide_type"), label.get("application_method"))

        c1, c2 = st.columns(2)
        if tank_dose:
            c1.metric(f"Mix per {tank:g} L tank", f"{tank_dose.amount} {tank_dose.unit}")
            c1.caption(f"Working: {tank_dose.how}")
        else:
            c1.warning("Dose not clear on the label. Ask the shop or call " + HELPLINE)
        if harvest:
            c2.metric("Earliest safe harvest", harvest.strftime("%d %b %Y"))
            c2.caption(f"Waiting period: {label['pre_harvest_interval_days']} days after spray")
        else:
            c2.warning("Waiting period not found on the label.")
        if acres:
            st.info(f"One tank covers about {acres} acre.")

        st.markdown(f"**Cautions for {soil_name}**")
        for n in notes:
            st.write("• " + n)

        if label.get("unreadable_or_missing"):
            st.warning("Could not read: " + ", ".join(label["unreadable_or_missing"]) + ". Retake the photo in better light.")

        if st.button(f"Explain in {language_label}"):
            with st.spinner("Writing explanation..."):
                facts = build_facts(label, use, tank_dose, acres, harvest, tank, soil_name, notes)
                st.markdown(explain(facts, language))

        with st.expander("Raw data read from the label"):
            st.json(label)

# ---------------------------------------------------------------- find a product
with find_tab:
    st.write(
        "Which product to use depends mainly on your **crop and the pest or disease**. "
        "Your soil type adds cautions. Suggestions come only from a verified list."
    )
    crop_in = st.text_input("Crop (e.g. cotton, tomato)")
    pest_in = st.text_input("Pest or disease (e.g. aphid, blight)")
    if st.button("Find products"):
        products = load_products()
        if not products:
            st.warning("The verified product list (data/registered_products.csv) is empty. Fill it from CIB&RC / agriculture university sources.")
        matches = find_products(crop_in, pest_in, products)
        cautions = soil_cautions(soil_key)
        if matches:
            st.dataframe(matches, use_container_width=True)
        elif products:
            st.info(f"No verified product found. Ask the local agriculture officer or call {HELPLINE}.")
        st.markdown(f"**Cautions for {soil_name}**")
        for n in cautions:
            st.write("• " + n)
        if products:
            with st.spinner("Writing explanation..."):
                st.markdown(explain_recommendation(crop_in, pest_in, soil_name, matches[:5], cautions, language))

st.divider()
st.caption(f"Always check the printed label. Unsure? Call {HELPLINE} or ask your local agriculture officer / Krishi Vigyan Kendra.")
