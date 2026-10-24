"""KisanLabel — interactive, creative, simple Streamlit UI.

DROP-IN INSTRUCTIONS (for the team):
  1. Copy this file into the root of the Spooky_Wookys project,
     next to app.py (so `kisanlabel/` is in the same folder).
  2. Run:  streamlit run ui.py
  3. No backend server needed. This UI calls the same kisanlabel
     modules as app.py / backend/ directly — Gemma only reads and
     explains, Python does all dose / harvest maths.

What is new vs the old app.py:
  - No sidebar (hidden on phones). Everything is in one thumb-friendly flow.
  - 3-step journey:  1 Photo  ->  2 Your field  ->  3 Result card
  - Tank slider + crop + spray date update the dose LIVE, with no
    second Gemma call — pure Python maths, so judges can play with it.
  - Dose is a big hero number, harvest is a visual timeline,
    safety is a tick-off checklist with a progress bar.
  - "Try a demo label" works with NO photo and NO API key, so a
    live demo never dies on stage. It is clearly marked DEMO.
"""
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

# ------------------------------------------------------------------ demo label
# Clearly fake, for UI demo only. Never presented as real advice.
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
    """segmented_control when available, selectbox otherwise (old Streamlit).
    FIX for KeyError: None: segmented_control returns None when the user
    clicks the selected pill again to deselect it. Never pass None on —
    fall back to the default option instead of crashing."""
    fallback = default or options[0]
    if hasattr(st, "segmented_control"):
        result = st.segmented_control(label, options, key=key, default=fallback)
        return result if result is not None else fallback
    return st.selectbox(label, options, key=key)


HEADINGS = {
    "Your dose — live": {
        "Hindi": "आपकी खुराक — लाइव", "Marathi": "तुमचा डोस — थेट",
        "Gujarati": "તમારો ડોઝ — લાઇવ", "Tamil": "உங்கள் அளவு — நேரலை",
        "Telugu": "మీ మోతాదు — ప్రత్యక్షంగా", "Kannada": "ನಿಮ್ಮ ಡೋಸ್ — ಲೈವ್",
        "Bengali": "আপনার ডোজ — লাইভ", "Punjabi": "ਤੁਹਾਡੀ ਖੁਰਾਕ — ਲਾਈਵ",
    },
    "When can you harvest?": {
        "Hindi": "कटाई कब कर सकते हैं?", "Marathi": "कापणी कधी करू शकता?",
        "Gujarati": "ક્યારે કાપણી કરી શકાય?", "Tamil": "எப்போது அறுவடை செய்யலாம்?",
        "Telugu": "ఎప్పుడు కోత చేయవచ్చు?", "Kannada": "ಯಾವಾಗ ಕೊಯ್ಲು ಮಾಡಬಹುದು?",
        "Bengali": "কখন ফসল কাটা যাবে?", "Punjabi": "ਕਦੋਂ ਵਾਢੀ ਕੀਤੀ ਜਾ ਸਕਦੀ ਹੈ?",
    },
    "Cautions for": {
        "Hindi": "सावधानियाँ", "Marathi": "काळजी",
        "Gujarati": "સાવચેતીઓ", "Tamil": "எச்சரிக்கைகள்",
        "Telugu": "జాగ్రత్తలు", "Kannada": "ಎಚ್ಚರಿಕೆಗಳು",
        "Bengali": "সতর্কতা", "Punjabi": "ਸਾਵਧਾਨੀਆਂ",
    },
    "Safety check — tick before you spray": {
        "Hindi": "सुरक्षा जाँच — छिड़काव से पहले टिक करें",
        "Marathi": "सुरक्षा तपासणी — फवारणीपूर्वी टिक करा",
        "Gujarati": "સલામતી તપાસ — છંટકાવ પહેલાં ટિક કરો",
        "Tamil": "பாதுகாப்பு சோதனை — தெளிப்பதற்கு முன் டிக் செய்யுங்கள்",
        "Telugu": "భద్రతా తనిఖీ — పిచికారీ చేసే ముందు టిక్ చేయండి",
        "Kannada": "ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ — ಸಿಂಪಡಿಸುವ ಮೊದಲು ಟಿಕ್ ಮಾಡಿ",
        "Bengali": "নিরাপত্তা পরীক্ষা — স্প্রে করার আগে টিক দিন",
        "Punjabi": "ਸੁਰੱਖਿਆ ਜਾਂਚ — ਸਪਰੇਅ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਟਿਕ ਕਰੋ",
    },
}


def tr(language_value, en, hi=None, mr=None):
    """Translate a UI heading for ALL 9 languages in LANGUAGES.
    Headings come from HEADINGS above; hi/mr args are kept as fallback."""
    if en in HEADINGS and language_value in HEADINGS[en]:
        return HEADINGS[en][language_value]
    if language_value == "Hindi" and hi:
        return hi
    if language_value == "Marathi" and mr:
        return mr
    return en


# Known strings only: soil cautions (from kisanlabel/soil.py) and generic
# PPE items. Arbitrary label text (safety_steps / first_aid as printed)
# is NOT dictionary-translated — Gemma's Explain paragraph translates it,
# and the original is kept so it can be checked against the bottle.
KNOWN_TEXT = {
    "Water drains fast here, so chemicals can wash down toward groundwater. Keep well away from wells and borewells.": {
        "Hindi": "यहाँ पानी जल्दी नीचे चला जाता है, इसलिए रसायन भूजल तक पहुँच सकते हैं। कुओं और बोरवेल से दूर रहें।",
        "Marathi": "येथे पाणी लवकर खाली जाते, त्यामुळे रसायने भूजलात जाऊ शकतात. विहिरी आणि बोअरवेलपासून दूर राहा.",
    },
    "Some products can hurt the crop more on light soil. Never go above the label dose.": {
        "Hindi": "हल्की मिट्टी में कुछ उत्पाद फसल को ज़्यादा नुकसान पहुँचा सकते हैं। लेबल की खुराक से ज़्यादा कभी न डालें।",
        "Marathi": "हलक्या मातीत काही उत्पादने पिकाला जास्त हानी पोहोचवू शकतात. लेबलवरील डोसपेक्षा जास्त कधीही टाकू नका.",
    },
    "Red soil is often low in organic matter, so chemicals stick to it less. Follow the label dose exactly.": {
        "Hindi": "लाल मिट्टी में अक्सर जैविक पदार्थ कम होता है, इसलिए रसायन कम चिपकते हैं। लेबल की खुराक बिल्कुल सही रखें।",
        "Marathi": "लाल मातीत सेंद्रिय पदार्थ अनेकदा कमी असतो, त्यामुळे रसायने कमी चिकटतात. लेबलवरील डोस अचूक पाळा.",
    },
    "In dry spells this soil cracks and chemicals can move down the cracks quickly.": {
        "Hindi": "सूखे में इस मिट्टी में दरारें पड़ जाती हैं और रसायन दरारों से जल्दी नीचे जा सकते हैं।",
        "Marathi": "कोरड्या काळात या मातीला भेगा पडतात आणि रसायने भेगांमधून लवकर खाली जाऊ शकतात.",
    },
    "After heavy rain it holds water and can run off. Avoid spraying just before rain.": {
        "Hindi": "भारी बारिश के बाद यह पानी रोकती है और बह सकती है। बारिश से ठीक पहले छिड़काव न करें।",
        "Marathi": "मुसळधार पावसानंतर ही पाणी धरून ठेवते आणि वाहून जाऊ शकते. पावसाच्या अगदी आधी फवारणी टाळा.",
    },
    "Loamy soil is fairly balanced. Follow the label dose and keep away from water sources.": {
        "Hindi": "दोमट मिट्टी काफी संतुलित होती है। लेबल की खुराक रखें और पानी के स्रोतों से दूर रहें।",
        "Marathi": "चिकणमाती बरीच संतुलित असते. लेबलवरील डोस पाळा आणि पाण्याच्या स्रोतांपासून दूर राहा.",
    },
    "This soil is porous and chemicals can wash through, like sandy soil. Keep away from wells and streams.": {
        "Hindi": "यह मिट्टी छिद्रयुक्त है और रसायन इसमें से बह सकते हैं, जैसे रेतीली मिट्टी में। कुओं और नालों से दूर रहें।",
        "Marathi": "ही माती सच्छिद्र आहे आणि रसायने त्यातून वाहून जाऊ शकतात, वाळूमय मातीप्रमाणे. विहिरी आणि ओढ्यांपासून दूर राहा.",
    },
    "Heavy clay holds chemicals longer, and runs off when waterlogged. Do not spray before heavy rain.": {
        "Hindi": "भारी चिकनी मिट्टी रसायनों को लंबे समय तक रोकती है, और पानी भरने पर बह जाती है। भारी बारिश से पहले छिड़काव न करें।",
        "Marathi": "जड चिकणमाती रसायने जास्त काळ धरून ठेवते आणि पाणी साचल्यावर वाहून जाते. मुसळधार पावसापूर्वी फवारणी करू नका.",
    },
    "This product works through the soil, so the right dose can change with soil type. Look for a light-soil or heavy-soil dose on the label, or ask the agriculture officer.": {
        "Hindi": "यह उत्पाद मिट्टी के माध्यम से काम करता है, इसलिए सही खुराक मिट्टी के प्रकार से बदल सकती है। लेबल पर हल्की या भारी मिट्टी की खुराक देखें, या कृषि अधिकारी से पूछें।",
        "Marathi": "हे उत्पादन मातीतून काम करते, त्यामुळे योग्य डोस मातीच्या प्रकारानुसार बदलू शकतो. लेबलवर हलक्या किंवा जड मातीचा डोस शोधा, किंवा कृषी अधिकाऱ्यांना विचारा.",
    },
    "This is sprayed on leaves, so soil type matters less. Still avoid spraying before rain.": {
        "Hindi": "यह पत्तियों पर छिड़का जाता है, इसलिए मिट्टी का प्रकार कम मायने रखता है। फिर भी बारिश से पहले छिड़काव से बचें।",
        "Marathi": "हे पानांवर फवारले जाते, त्यामुळे मातीचा प्रकार कमी महत्त्वाचा आहे. तरीही पावसापूर्वी फवारणी टाळा.",
    },
    "Wear gloves": {"Hindi": "दस्ताने पहनें", "Marathi": "हातमोजे घाला"},
    "Wear a mask": {"Hindi": "मास्क पहनें", "Marathi": "मास्क घाला"},
    "Wear long sleeves": {"Hindi": "लंबी आस्तीन पहनें", "Marathi": "लांब बाह्या घाला"},
    "Wear goggles": {"Hindi": "चश्मा पहनें", "Marathi": "गॉगल घाला"},
    "Wash hands after spraying": {"Hindi": "छिड़काव के बाद हाथ धोएं", "Marathi": "फवारणीनंतर हात धुवा"},
    "Wear gloves, mask and long sleeves": {"Hindi": "दस्ताने, मास्क और लंबी आस्तीन पहनें", "Marathi": "हातमोजे, मास्क आणि लांब बाह्या घाला"},
    "Do not eat, drink or smoke while spraying": {"Hindi": "छिड़काव करते समय खाना, पीना या धूम्रपान न करें", "Marathi": "फवारणी करताना खाऊ, पिऊ किंवा धूम्रपान करू नका"},
}


# Extended to all languages. UI translations are best-effort and simple;
# check by a native speaker before any real rollout. Gemma's Explain
# paragraph is the full translation for arbitrary label text.
SOIL_EXTENDED = {
    "Water drains fast here, so chemicals can wash down toward groundwater. Keep well away from wells and borewells.": {
        "Gujarati": "અહીં પાણી ઝડપથી નીચે જાય છે, તેથી રસાયણો ભૂગર્ભજળ સુધી પહોંચી શકે છે. કૂવા અને બોરવેલથી દૂર રહો.",
        "Tamil": "இங்கு நீர் வேகமாக கீழே செல்கிறது, எனவே இரசாயனங்கள் நிலத்தடி நீரை அடையலாம். கிணறுகள் மற்றும் போர்வெல்களில் இருந்து விலகி இருங்கள்.",
        "Telugu": "ఇక్కడ నీరు వేగంగా క్రిందికి వెళుతుంది, కాబట్టి రసాయనాలు భూగర్భ జలాలకు చేరవచ్చు. బావులు, బోర్‌వెల్‌లకు దూరంగా ఉండండి.",
        "Kannada": "ಇಲ್ಲಿ ನೀರು ವೇಗವಾಗಿ ಕೆಳಗೆ ಹೋಗುತ್ತದೆ, ಆದ್ದರಿಂದ ರಾಸಾಯನಿಕಗಳು ಅಂತರ್ಜಲವನ್ನು ತಲುಪಬಹುದು. ಬಾವಿಗಳು ಮತ್ತು ಬೋರ್‌ವೆಲ್‌ಗಳಿಂದ ದೂರವಿರಿ.",
        "Bengali": "এখানে জল দ্রুত নিচে চলে যায়, তাই রাসায়নিক ভূগর্ভস্থ জলে পৌঁছতে পারে। কূপ ও বোরওয়েল থেকে দূরে থাকুন।",
        "Punjabi": "ਇੱਥੇ ਪਾਣੀ ਤੇਜ਼ੀ ਨਾਲ ਹੇਠਾਂ ਜਾਂਦਾ ਹੈ, ਇਸ ਲਈ ਰਸਾਇਣ ਭੂਮੀਗਤ ਪਾਣੀ ਤੱਕ ਪਹੁੰਚ ਸਕਦੇ ਹਨ। ਖੂਹਾਂ ਅਤੇ ਬੋਰਵੈੱਲਾਂ ਤੋਂ ਦੂਰ ਰਹੋ।",
    },
    "Some products can hurt the crop more on light soil. Never go above the label dose.": {
        "Gujarati": "હળવી માટીમાં કેટલાક ઉત્પાદનો પાકને વધુ નુકસાન પહોંચાડી શકે છે. લેબલના ડોઝથી વધુ ક્યારેય ન નાખો.",
        "Tamil": "இலகுவான மண்ணில் சில பொருட்கள் பயிருக்கு அதிக தீங்கு விளைவிக்கும். லேபிள் அளவை விட அதிகமாக ஒருபோதும் பயன்படுத்தாதீர்கள்.",
        "Telugu": "తేలికపాటి నేలలో కొన్ని ఉత్పత్తులు పంటకు ఎక్కువ హాని చేయవచ్చు. లేబుల్ మోతాదు కంటే ఎక్కువ ఎప్పుడూ వేయకండి.",
        "Kannada": "ಹಗುರವಾದ ಮಣ್ಣಿನಲ್ಲಿ ಕೆಲವು ಉತ್ಪನ್ನಗಳು ಬೆಳೆಗೆ ಹೆಚ್ಚು ಹಾನಿ ಮಾಡಬಹುದು. ಲೇಬಲ್ ಡೋಸ್‌ಗಿಂತ ಹೆಚ್ಚು ಎಂದಿಗೂ ಹಾಕಬೇಡಿ.",
        "Bengali": "হালকা মাটিতে কিছু পণ্য ফসলের বেশি ক্ষতি করতে পারে। লেবেলের ডোজের বেশি কখনো দেবেন না।",
        "Punjabi": "ਹਲਕੀ ਮਿੱਟੀ ਵਿੱਚ ਕੁਝ ਉਤਪਾਦ ਫਸਲ ਨੂੰ ਵੱਧ ਨੁਕਸਾਨ ਪਹੁੰਚਾ ਸਕਦੇ ਹਨ। ਲੇਬਲ ਦੀ ਖੁਰਾਕ ਤੋਂ ਵੱਧ ਕਦੇ ਨਾ ਪਾਓ।",
    },
    "Red soil is often low in organic matter, so chemicals stick to it less. Follow the label dose exactly.": {
        "Gujarati": "લાલ માટીમાં ઘણીવાર કાર્બનિક પદાર્થ ઓછો હોય છે, તેથી રસાયણો ઓછા ચોંટે છે. લેબલનો ડોઝ બરાબર પાળો.",
        "Tamil": "சிவப்பு மண்ணில் பெரும்பாலும் கரிமப் பொருள் குறைவாக இருக்கும், எனவே இரசாயனங்கள் குறைவாக ஒட்டும். லேபிள் அளவை சரியாக பின்பற்றுங்கள்.",
        "Telugu": "ఎర్ర నేలలో తరచుగా సేంద్రీయ పదార్థం తక్కువగా ఉంటుంది, కాబట్టి రసాయనాలు తక్కువగా అంటుకుంటాయి. లేబుల్ మోతాదును ఖచ్చితంగా పాటించండి.",
        "Kannada": "ಕೆಂಪು ಮಣ್ಣಿನಲ್ಲಿ ಹೆಚ್ಚಾಗಿ ಸಾವಯವ ವಸ್ತು ಕಡಿಮೆ ಇರುತ್ತದೆ, ಆದ್ದರಿಂದ ರಾಸಾಯನಿಕಗಳು ಕಡಿಮೆ ಅಂಟಿಕೊಳ್ಳುತ್ತವೆ. ಲೇಬಲ್ ಡೋಸ್ ಅನ್ನು ನಿಖರವಾಗಿ ಪಾಲಿಸಿ.",
        "Bengali": "লাল মাটিতে প্রায়ই জৈব পদার্থ কম থাকে, তাই রাসায়নিক কম লেগে থাকে। লেবেলের ডোজ ঠিকঠাক মেনে চলুন।",
        "Punjabi": "ਲਾਲ ਮਿੱਟੀ ਵਿੱਚ ਅਕਸਰ ਜੈਵਿਕ ਪਦਾਰਥ ਘੱਟ ਹੁੰਦਾ ਹੈ, ਇਸ ਲਈ ਰਸਾਇਣ ਘੱਟ ਚਿਪਕਦੇ ਹਨ। ਲੇਬਲ ਦੀ ਖੁਰਾਕ ਬਿਲਕੁਲ ਪਾਲੋ।",
    },
    "In dry spells this soil cracks and chemicals can move down the cracks quickly.": {
        "Gujarati": "સૂકા સમયમાં આ માટીમાં તિરાડો પડે છે અને રસાયણો તિરાડોમાંથી ઝડપથી નીચે જઈ શકે છે.",
        "Tamil": "வறண்ட காலத்தில் இந்த மண் வெடிக்கும், இரசாயனங்கள் வெடிப்புகள் வழியாக விரைவாக கீழே செல்லலாம்.",
        "Telugu": "పొడి కాలంలో ఈ నేల పగుళ్లు వస్తుంది, రసాయనాలు పగుళ్ల ద్వారా వేగంగా క్రిందికి వెళ్ళవచ్చు.",
        "Kannada": "ಶುಷ್ಕ ಕಾಲದಲ್ಲಿ ಈ ಮಣ್ಣು ಬಿರುಕು ಬಿಡುತ್ತದೆ ಮತ್ತು ರಾಸಾಯನಿಕಗಳು ಬಿರುಕುಗಳ ಮೂಲಕ ವೇಗವಾಗಿ ಕೆಳಗೆ ಹೋಗಬಹುದು.",
        "Bengali": "শুষ্ক সময়ে এই মাটি ফেটে যায় এবং রাসায়নিক ফাটল দিয়ে দ্রুত নিচে যেতে পারে।",
        "Punjabi": "ਸੁੱਕੇ ਸਮੇਂ ਵਿੱਚ ਇਹ ਮਿੱਟੀ ਫਟ ਜਾਂਦੀ ਹੈ ਅਤੇ ਰਸਾਇਣ ਤਰੇੜਾਂ ਰਾਹੀਂ ਤੇਜ਼ੀ ਨਾਲ ਹੇਠਾਂ ਜਾ ਸਕਦੇ ਹਨ।",
    },
    "After heavy rain it holds water and can run off. Avoid spraying just before rain.": {
        "Gujarati": "ભારે વરસાદ પછી તે પાણી રોકે છે અને વહી શકે છે. વરસાદ પહેલાં તરત છંટકાવ ટાળો.",
        "Tamil": "கனமழைக்குப் பிறகு இது நீரைத் தக்கவைத்து வழிந்தோடலாம். மழைக்கு முன் தெளிப்பதைத் தவிர்க்கவும்.",
        "Telugu": "భారీ వర్షం తర్వాత ఇది నీటిని నిలుపుకుని ప్రవహించవచ్చు. వర్షానికి ముందు పిచికారీ చేయడం మానుకోండి.",
        "Kannada": "ಭಾರೀ ಮಳೆಯ ನಂತರ ಇದು ನೀರನ್ನು ಹಿಡಿದಿಟ್ಟು ಹರಿದು ಹೋಗಬಹುದು. ಮಳೆಗೆ ಮುನ್ನ ಸಿಂಪಡಿಸುವುದನ್ನು ತಪ್ಪಿಸಿ.",
        "Bengali": "ভারী বৃষ্টির পর এটি জল ধরে রাখে এবং বয়ে যেতে পারে। বৃষ্টির ঠিক আগে স্প্রে করা এড়িয়ে চলুন।",
        "Punjabi": "ਭਾਰੀ ਮੀਂਹ ਤੋਂ ਬਾਅਦ ਇਹ ਪਾਣੀ ਰੋਕ ਲੈਂਦੀ ਹੈ ਅਤੇ ਵਹਿ ਸਕਦੀ ਹੈ। ਮੀਂਹ ਤੋਂ ਠੀਕ ਪਹਿਲਾਂ ਸਪਰੇਅ ਕਰਨ ਤੋਂ ਬਚੋ।",
    },
    "Loamy soil is fairly balanced. Follow the label dose and keep away from water sources.": {
        "Gujarati": "ચીકણી માટી ઘણી સંતુલિત હોય છે. લેબલનો ડોઝ પાળો અને પાણીના સ્ત્રોતોથી દૂર રહો.",
        "Tamil": "வளமான மண் மிகவும் சமநிலையானது. லேபிள் அளவைப் பின்பற்றி, நீர் ஆதாரங்களில் இருந்து விலகி இருங்கள்.",
        "Telugu": "లోమీ నేల చాలా సమతుల్యంగా ఉంటుంది. లేబుల్ మోతాదును పాటించండి మరియు నీటి వనరులకు దూరంగా ఉండండి.",
        "Kannada": "ಲೋಮಿ ಮಣ್ಣು ಸಾಕಷ್ಟು ಸಮತೋಲಿತವಾಗಿದೆ. ಲೇಬಲ್ ಡೋಸ್ ಪಾಲಿಸಿ ಮತ್ತು ನೀರಿನ ಮೂಲಗಳಿಂದ ದೂರವಿರಿ.",
        "Bengali": "দোআঁশ মাটি বেশ ভারসাম্যপূর্ণ। লেবেলের ডোজ মেনে চলুন এবং জলের উৎস থেকে দূরে থাকুন।",
        "Punjabi": "ਦੋਮਟ ਮਿੱਟੀ ਕਾਫ਼ੀ ਸੰਤੁਲਿਤ ਹੁੰਦੀ ਹੈ। ਲੇਬਲ ਦੀ ਖੁਰਾਕ ਪਾਲੋ ਅਤੇ ਪਾਣੀ ਦੇ ਸਰੋਤਾਂ ਤੋਂ ਦੂਰ ਰਹੋ।",
    },
    "This soil is porous and chemicals can wash through, like sandy soil. Keep away from wells and streams.": {
        "Gujarati": "આ માટી છિદ્રાળુ છે અને રસાયણો તેમાંથી ધોવાઈ શકે છે, રેતાળ માટીની જેમ. કૂવા અને ઝરણાથી દૂર રહો.",
        "Tamil": "இந்த மண் துளைகள் நிறைந்தது, மணல் மண்ணைப் போல இரசாயனங்கள் அதன் வழியாக கழுவப்படலாம். கிணறுகள் மற்றும் ஓடைகளில் இருந்து விலகி இருங்கள்.",
        "Telugu": "ఈ నేల రంధ్రాలు కలిగి ఉంటుంది, ఇసుక నేలలాగా రసాయనాలు దాని గుండా కొట్టుకుపోవచ్చు. బావులు, వాగులకు దూరంగా ఉండండి.",
        "Kannada": "ಈ ಮಣ್ಣು ರಂಧ್ರಯುಕ್ತವಾಗಿದೆ ಮತ್ತು ಮರಳು ಮಣ್ಣಿನಂತೆ ರಾಸಾಯನಿಕಗಳು ಅದರ ಮೂಲಕ ತೊಳೆದು ಹೋಗಬಹುದು. ಬಾವಿಗಳು ಮತ್ತು ಹೊಳೆಗಳಿಂದ ದೂರವಿರಿ.",
        "Bengali": "এই মাটি ছিদ্রযুক্ত এবং বালি মাটির মতো রাসায়নিক এর মধ্য দিয়ে ধুয়ে যেতে পারে। কূপ ও ঝরনা থেকে দূরে থাকুন।",
        "Punjabi": "ਇਹ ਮਿੱਟੀ ਛੇਦ ਵਾਲੀ ਹੈ ਅਤੇ ਰੇਤਲੀ ਮਿੱਟੀ ਵਾਂਗ ਰਸਾਇਣ ਇਸ ਵਿੱਚੋਂ ਧੋਤੇ ਜਾ ਸਕਦੇ ਹਨ। ਖੂਹਾਂ ਅਤੇ ਨਾਲਿਆਂ ਤੋਂ ਦੂਰ ਰਹੋ।",
    },
    "Heavy clay holds chemicals longer, and runs off when waterlogged. Do not spray before heavy rain.": {
        "Gujarati": "ભારે ચીકણી માટી રસાયણોને લાંબા સમય સુધી રોકે છે, અને પાણી ભરાય ત્યારે વહી જાય છે. ભારે વરસાદ પહેલાં છંટકાવ ન કરો.",
        "Tamil": "கனமான களிமண் இரசாயனங்களை நீண்ட நேரம் வைத்திருக்கும், நீர் தேங்கும்போது வழிந்தோடும். கனமழைக்கு முன் தெளிக்காதீர்கள்.",
        "Telugu": "భారీ బంకమట్టి రసాయనాలను ఎక్కువసేపు నిలుపుకుంటుంది, నీరు నిలిచినప్పుడు ప్రవహిస్తుంది. భారీ వర్షానికి ముందు పిచికారీ చేయకండి.",
        "Kannada": "ಭಾರೀ ಜೇಡಿಮಣ್ಣು ರಾಸಾಯನಿಕಗಳನ್ನು ಹೆಚ್ಚು ಕಾಲ ಹಿಡಿದಿಟ್ಟುಕೊಳ್ಳುತ್ತದೆ ಮತ್ತು ನೀರು ನಿಂತಾಗ ಹರಿದು ಹೋಗುತ್ತದೆ. ಭಾರೀ ಮಳೆಗೆ ಮುನ್ನ ಸಿಂಪಡಿಸಬೇಡಿ.",
        "Bengali": "ভারী এঁটেল মাটি রাসায়নিক দীর্ঘক্ষণ ধরে রাখে, এবং জল জমলে বয়ে যায়। ভারী বৃষ্টির আগে স্প্রে করবেন না।",
        "Punjabi": "ਭਾਰੀ ਚਿਕਣੀ ਮਿੱਟੀ ਰਸਾਇਣਾਂ ਨੂੰ ਲੰਬੇ ਸਮੇਂ ਤੱਕ ਰੋਕਦੀ ਹੈ, ਅਤੇ ਪਾਣੀ ਭਰਨ 'ਤੇ ਵਹਿ ਜਾਂਦੀ ਹੈ। ਭਾਰੀ ਮੀਂਹ ਤੋਂ ਪਹਿਲਾਂ ਸਪਰੇਅ ਨਾ ਕਰੋ।",
    },
    "This product works through the soil, so the right dose can change with soil type. Look for a light-soil or heavy-soil dose on the label, or ask the agriculture officer.": {
        "Gujarati": "આ ઉત્પાદન માટી દ્વારા કામ કરે છે, તેથી સાચો ડોઝ માટીના પ્રકાર પ્રમાણે બદલાઈ શકે છે. લેબલ પર હળવી કે ભારે માટીનો ડોઝ જુઓ, અથવા કૃષિ અધિકારીને પૂછો.",
        "Tamil": "இந்த பொருள் மண் வழியாக செயல்படுகிறது, எனவே சரியான அளவு மண் வகையைப் பொறுத்து மாறலாம். லேபிளில் இலகுவான அல்லது கனமான மண் அளவைப் பாருங்கள், அல்லது வேளாண் அதிகாரியிடம் கேளுங்கள்.",
        "Telugu": "ఈ ఉత్పత్తి నేల ద్వారా పనిచేస్తుంది, కాబట్టి సరైన మోతాదు నేల రకాన్ని బట్టి మారవచ్చు. లేబుల్‌పై తేలికపాటి లేదా భారీ నేల మోతాదును చూడండి, లేదా వ్యవసాయ అధికారిని అడగండి.",
        "Kannada": "ಈ ಉತ್ಪನ್ನವು ಮಣ್ಣಿನ ಮೂಲಕ ಕೆಲಸ ಮಾಡುತ್ತದೆ, ಆದ್ದರಿಂದ ಸರಿಯಾದ ಡೋಸ್ ಮಣ್ಣಿನ ಪ್ರಕಾರವನ್ನು ಅವಲಂಬಿಸಿ ಬದಲಾಗಬಹುದು. ಲೇಬಲ್‌ನಲ್ಲಿ ಹಗುರ ಅಥವಾ ಭಾರೀ ಮಣ್ಣಿನ ಡೋಸ್ ನೋಡಿ, ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಕೇಳಿ.",
        "Bengali": "এই পণ্য মাটির মাধ্যমে কাজ করে, তাই সঠিক ডোজ মাটির ধরনের উপর নির্ভর করে বদলাতে পারে। লেবেলে হালকা বা ভারী মাটির ডোজ দেখুন, অথবা কৃষি আধিকারিককে জিজ্ঞাসা করুন।",
        "Punjabi": "ਇਹ ਉਤਪਾਦ ਮਿੱਟੀ ਰਾਹੀਂ ਕੰਮ ਕਰਦਾ ਹੈ, ਇਸ ਲਈ ਸਹੀ ਖੁਰਾਕ ਮਿੱਟੀ ਦੀ ਕਿਸਮ ਅਨੁਸਾਰ ਬਦਲ ਸਕਦੀ ਹੈ। ਲੇਬਲ 'ਤੇ ਹਲਕੀ ਜਾਂ ਭਾਰੀ ਮਿੱਟੀ ਦੀ ਖੁਰਾਕ ਵੇਖੋ, ਜਾਂ ਖੇਤੀਬਾੜੀ ਅਧਿਕਾਰੀ ਨੂੰ ਪੁੱਛੋ।",
    },
    "This is sprayed on leaves, so soil type matters less. Still avoid spraying before rain.": {
        "Gujarati": "આ પાંદડા પર છંટાય છે, તેથી માટીનો પ્રકાર ઓછો મહત્વનો છે. છતાં વરસાદ પહેલાં છંટકાવ ટાળો.",
        "Tamil": "இது இலைகளில் தெளிக்கப்படுகிறது, எனவே மண் வகை குறைவாக முக்கியம். இருப்பினும் மழைக்கு முன் தெளிப்பதைத் தவிர்க்கவும்.",
        "Telugu": "ఇది ఆకులపై పిచికారీ చేయబడుతుంది, కాబట్టి నేల రకం తక్కువ ముఖ్యం. అయినప్పటికీ వర్షానికి ముందు పిచికారీ చేయడం మానుకోండి.",
        "Kannada": "ಇದನ್ನು ಎಲೆಗಳ ಮೇಲೆ ಸಿಂಪಡಿಸಲಾಗುತ್ತದೆ, ಆದ್ದರಿಂದ ಮಣ್ಣಿನ ಪ್ರಕಾರ ಕಡಿಮೆ ಮುಖ್ಯ. ಆದರೂ ಮಳೆಗೆ ಮುನ್ನ ಸಿಂಪಡಿಸುವುದನ್ನು ತಪ್ಪಿಸಿ.",
        "Bengali": "এটি পাতায় স্প্রে করা হয়, তাই মাটির ধরন কম গুরুত্বপূর্ণ। তবুও বৃষ্টির আগে স্প্রে করা এড়িয়ে চলুন।",
        "Punjabi": "ਇਹ ਪੱਤਿਆਂ 'ਤੇ ਸਪਰੇਅ ਕੀਤਾ ਜਾਂਦਾ ਹੈ, ਇਸ ਲਈ ਮਿੱਟੀ ਦੀ ਕਿਸਮ ਘੱਟ ਮਹੱਤਵਪੂਰਨ ਹੈ। ਫਿਰ ਵੀ ਮੀਂਹ ਤੋਂ ਪਹਿਲਾਂ ਸਪਰੇਅ ਕਰਨ ਤੋਂ ਬਚੋ।",
    },
    "Wear gloves": {
        "Gujarati": "મોજા પહેરો", "Tamil": "கையுறைகள் அணியுங்கள்",
        "Telugu": "గ్లౌజులు ధరించండి", "Kannada": "ಕೈಗವಸುಗಳನ್ನು ಧರಿಸಿ",
        "Bengali": "গ্লাভস পরুন", "Punjabi": "ਦਸਤਾਨੇ ਪਾਓ",
    },
    "Wear a mask": {
        "Gujarati": "માસ્ક પહેરો", "Tamil": "முகமூடி அணியுங்கள்",
        "Telugu": "మాస్క్ ధరించండి", "Kannada": "ಮಾಸ್ಕ್ ಧರಿಸಿ",
        "Bengali": "মাস্ক পরুন", "Punjabi": "ਮਾਸਕ ਪਾਓ",
    },
    "Wear long sleeves": {
        "Gujarati": "લાંબી બાંય પહેરો", "Tamil": "நீண்ட கைகள் கொண்ட ஆடை அணியுங்கள்",
        "Telugu": "పొడవాటి చేతులు ఉన్న దుస్తులు ధరించండి", "Kannada": "ಉದ್ದ ತೋಳುಗಳನ್ನು ಧರಿಸಿ",
        "Bengali": "লম্বা হাতা পরুন", "Punjabi": "ਲੰਬੀਆਂ ਬਾਹਵਾਂ ਪਾਓ",
    },
    "Wear goggles": {
        "Gujarati": "ગોગલ્સ પહેરો", "Tamil": "கண்ணாடி அணியுங்கள்",
        "Telugu": "గాగుల్స్ ధరించండి", "Kannada": "ಗಾಗಲ್ಸ್ ಧರಿಸಿ",
        "Bengali": "গগলস পরুন", "Punjabi": "ਗੋਗਲਜ਼ ਪਾਓ",
    },
    "Wash hands after spraying": {
        "Gujarati": "છંટકાવ પછી હાથ ધુઓ", "Tamil": "தெளித்த பிறகு கைகளை கழுவுங்கள்",
        "Telugu": "పిచికారీ చేసిన తర్వాత చేతులు కడుక్కోండి", "Kannada": "ಸಿಂಪಡಿಸಿದ ನಂತರ ಕೈಗಳನ್ನು ತೊಳೆಯಿರಿ",
        "Bengali": "স্প্রে করার পর হাত ধুয়ে নিন", "Punjabi": "ਸਪਰੇਅ ਕਰਨ ਤੋਂ ਬਾਅਦ ਹੱਥ ਧੋਵੋ",
    },
    "Wear gloves, mask and long sleeves": {
        "Gujarati": "મોજા, માસ્ક અને લાંબી બાંય પહેરો", "Tamil": "கையுறைகள், முகமூடி மற்றும் நீண்ட கைகள் கொண்ட ஆடை அணியுங்கள்",
        "Telugu": "గ్లౌజులు, మాస్క్ మరియు పొడవాటి చేతులు ఉన్న దుస్తులు ధరించండి", "Kannada": "ಕೈಗವಸುಗಳು, ಮಾಸ್ಕ್ ಮತ್ತು ಉದ್ದ ತೋಳುಗಳನ್ನು ಧರಿಸಿ",
        "Bengali": "গ্লাভস, মাস্ক এবং লম্বা হাতা পরুন", "Punjabi": "ਦਸਤਾਨੇ, ਮਾਸਕ ਅਤੇ ਲੰਬੀਆਂ ਬਾਹਵਾਂ ਪਾਓ",
    },
    "Do not eat, drink or smoke while spraying": {
        "Gujarati": "છંટકાવ કરતી વખતે ખાવું, પીવું કે ધૂમ્રપાન કરવું નહીં", "Tamil": "தெளிக்கும்போது சாப்பிடவோ, குடிக்கவோ, புகைபிடிக்கவோ வேண்டாம்",
        "Telugu": "పిచికారీ చేస్తున్నప్పుడు తినకండి, తాగకండి లేదా పొగ తాగకండి", "Kannada": "ಸಿಂಪಡಿಸುವಾಗ ತಿನ್ನಬೇಡಿ, ಕುಡಿಯಬೇಡಿ ಅಥವಾ ಧೂಮಪಾನ ಮಾಡಬೇಡಿ",
        "Bengali": "স্প্রে করার সময় খাবেন না, পান করবেন না বা ধূমপান করবেন না", "Punjabi": "ਸਪਰੇਅ ਕਰਦੇ ਸਮੇਂ ਖਾਓ ਨਾ, ਪੀਓ ਨਾ ਜਾਂ ਸਿਗਰਟ ਨਾ ਪੀਓ",
    },
}


def tr_known(text, language_value):
    """Translate a known string, else return it unchanged (label original)."""
    if text in KNOWN_TEXT and language_value in KNOWN_TEXT[text]:
        return KNOWN_TEXT[text][language_value]
    if text in SOIL_EXTENDED and language_value in SOIL_EXTENDED[text]:
        return SOIL_EXTENDED[text][language_value]
    return text


def safe_explain(fn, *args):
    """Call a Gemma explain function, retrying once on 'client has been closed'.
    Root cause (verified): explain.py/extract.py create the google-genai
    client inline — get_client().models.generate_content(...) — so Python
    can garbage-collect the client mid-request and its finalizer closes
    the HTTP pool. The fix below (persistent client in session_state)
    prevents that; this retry is only a backup, and it first drops the
    closed client so the retry builds a fresh one."""
    try:
        return fn(*args)
    except Exception as e:
        if "client has been closed" in str(e).lower():
            st.session_state.pop("genai_client", None)
            return fn(*args)
        raise


# ------------------------------------------------------------------ ROOT FIX
# Hold ONE google-genai client in session_state and make explain/extract
# use it, instead of creating a throwaway client inline on every call.
# A throwaway client can be garbage-collected mid-request, closing its
# HTTP pool — that is exactly the "client has been closed" error.
# This is lazy: it only creates a client on the first Gemma call, so a
# missing API key still shows the friendly error, not a startup crash.
try:
    import kisanlabel.client as _client_mod
    import kisanlabel.explain as _explain_mod
    import kisanlabel.extract as _extract_mod

    def _get_persistent_client():
        if "genai_client" not in st.session_state:
            st.session_state["genai_client"] = _client_mod.get_client()
        return st.session_state["genai_client"]

    _explain_mod.get_client = _get_persistent_client
    _extract_mod.get_client = _get_persistent_client
except Exception:
    pass  # if kisanlabel is not importable here, the original code path runs


# ------------------------------------------------------------------ page + style
st.set_page_config(page_title="KisanLabel 🌾", page_icon="🌾", layout="centered")
st.markdown("""
<style>
  .main { max-width: 760px; }
  html, body { font-size: 18px; }
  h1 { font-size: 2.2rem !important; line-height: 1.1; }
  h2, h3 { margin-top: 1.2rem !important; }
  .stButton > button {
    width: 100%; background: #1B5E20; color: #fff; border: none;
    font-size: 1.15rem; font-weight: 800; padding: 0.9rem 1rem; border-radius: 16px;
  }
  .stButton > button:hover { background: #2E7D32; color: #fff; }
  .hero {
    background: linear-gradient(135deg, #E8F5E9, #FFF8E1);
    border: 2px dashed #81C784; border-radius: 22px; padding: 1.2rem 1.4rem;
  }
  .hero p { margin: 0.25rem 0; color: #263238; }
  .label-card {
    background: #FFFDF5; border: 2px solid #1B5E20; border-radius: 20px;
    padding: 1.2rem 1.4rem; margin: 1rem 0;
  }
  .dose-hero {
    background: #1B5E20; color: #fff; border-radius: 20px;
    padding: 1.4rem; text-align: center; margin: 1rem 0;
  }
  .dose-hero .big { font-size: 2.8rem; font-weight: 900; line-height: 1; }
  .dose-hero .small { opacity: 0.92; margin-top: 0.4rem; }
  .timeline { display: flex; gap: 0.6rem; text-align: center; }
  .timeline > div {
    flex: 1; background: #F1F8E9; border-radius: 14px; padding: 0.8rem 0.4rem;
  }
  .timeline b { display: block; font-size: 1.05rem; }
  .stepbar { font-weight: 800; color: #1B5E20; letter-spacing: 0.02em; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ header + steps
label = st.session_state.get("label")
step = 3 if label else (2 if st.session_state.get("photo_done") else 1)
st.markdown(f"""
<div class="hero">
  <h1>🌾 KisanLabel</h1>
  <p><b>Photo of a label → dose for <i>your</i> tank, in <i>your</i> language.</b></p>
  <p>For farmers, farm workers and shop staff. No guessing — if it is not on the label, we say so.</p>
</div>
<p class="stepbar">{'✅' if step > 1 else '①'} Photo &nbsp;→&nbsp; {'✅' if step > 2 else '②'} Your field &nbsp;→&nbsp; {'✅' if step > 2 else '③'} Result card</p>
""", unsafe_allow_html=True)

mode = pick("What do you want to do?", ["📷 Scan a label", "🔎 Find a product"], key="mode")

# Shared field controls — changing these NEVER re-calls Gemma, only Python maths.
st.markdown("### 🌾 Your field")
col_a, col_b = st.columns(2)
with col_a:
    lang_label = pick("Language", list(LANGUAGES), key="lang")
with col_b:
    soil_key = st.selectbox("Soil type", list(SOILS), format_func=SOILS.get, key="soil")
language = LANGUAGES.get(lang_label, "English")  # belt-and-braces: never crash on None
soil_name = SOILS[soil_key]
tank = st.slider("Sprayer tank size (litres) — drag it, the dose updates live",
                 min_value=5, max_value=25, value=16, step=1, key="tank")
spray_date = st.date_input("Spray date", dt.date.today(), key="spray_date")
st.caption("💡 Dragging the tank slider does not call the AI again. The dose is recalculated in Python. Changing language changes the headings below — tap 'Explain' again to re-translate the paragraph.")

# ------------------------------------------------------------------ scan a label
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

    # ---- result card, styled like a printed label
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
          <div style="font-size:1rem; opacity:0.9;">MIX IN ONE {tank:g} L TANK</div>
          <div class="big">{tank_dose.amount} {tank_dose.unit}</div>
          <div class="small">Working: {tank_dose.how} &nbsp;·&nbsp; One tank covers about {acres} acre</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"Dose not clear on the label. Do not guess — ask the shop or call {HELPLINE}.")

    st.markdown(f"### ③ {tr(language, 'When can you harvest?', 'कटाई कब कर सकते हैं?', 'कापणी कधी करू शकता?')}")
    if harvest:
        st.markdown(f"""
        <div class="timeline">
          <div>🌱<b>Spray</b>{spray_date.strftime("%d %b %Y")}</div>
          <div>⏳<b>Wait</b>{label['pre_harvest_interval_days']} days</div>
          <div>🌾<b>Harvest from</b>{harvest.strftime("%d %b %Y")}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Waiting period not found on the label.")

    st.markdown(f"### 🪱 {tr(language, 'Cautions for', 'सावधानियाँ', 'काळजी')} {soil_name}")
    for n in notes:
        st.write("• " + tr_known(n, language))
    if label.get("unreadable_or_missing"):
        st.warning("Could not read: " + ", ".join(label["unreadable_or_missing"]) + ". Retake in better light.")

    # ---- interactive safety checklist (user ticks, progress fills)
    st.markdown(f"### 🧤 {tr(language, 'Safety check — tick before you spray', 'सुरक्षा जाँच — छिड़काव से पहले टिक करें', 'सुरक्षा तपासणी — फवारणीपूर्वी टिक करा')}")
    ppe_items = list(dict.fromkeys((label.get("safety_steps") or []) + [
        "Wear gloves", "Wear a mask", "Wear long sleeves", "Wear goggles", "Wash hands after spraying"]))
    # Checkbox labels are translated for known items; the key stays English
    # so ticking survives a language switch.
    ticks = [st.checkbox(tr_known(item, language), key=f"ppe_{i}") for i, item in enumerate(ppe_items)]
    st.caption("Label wording stays as printed so you can check it against the bottle — the Explain paragraph below translates it in full.")
    done = sum(ticks)
    st.progress(done / max(len(ticks), 1), text=f"Safety ready: {done}/{len(ticks)} ticked")
    if done == len(ticks):
        st.success("✅ All safety steps ticked. Still follow the printed label.")
    if label.get("first_aid"):
        with st.expander("🩹 First aid (from the label)"):
            for f in label["first_aid"]:
                st.write("• " + f)

    # Explain is STORED in session_state, so it does not vanish when you
    # move the tank slider, and it is re-generated in the NEW language
    # when you tap it again after switching language.
    if st.button(f"🗣️ Explain in {lang_label}"):
        with st.spinner("Writing a simple explanation…"):
            try:
                facts = build_facts(label, use, tank_dose, acres, harvest, tank, soil_name, notes)
                # Retry once if the previous run's HTTP client was closed
                # (e.g. you clicked / changed something mid-request).
                st.session_state["explanation"] = safe_explain(explain, facts, language)
                st.session_state["explanation_lang"] = language
            except Exception as e:
                # FIX: never crash the whole page on a missing/invalid API key.
                # The dose card above still works — only Explain needs Gemma.
                st.error(f"Could not write the explanation: {e}")
                st.info("Fix: copy .env.example to .env, paste your free Gemini API key from Google AI Studio into it, then restart Streamlit (Ctrl + C, then run it again). Do not commit .env to GitHub.")
    if st.session_state.get("explanation"):
        if st.session_state.get("explanation_lang") != language:
            st.info(f"Language changed to {lang_label}. Tap 'Explain in {lang_label}' again to translate this result.")
        st.markdown(st.session_state["explanation"])
    with st.expander("🔍 Raw data read from the label (for judges)"):
        st.json(label)

# ------------------------------------------------------------------ find a product
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
                    st.markdown(safe_explain(explain_recommendation, crop_in, pest_in, soil_name, matches[:5], cautions, language))
                except Exception as e:
                    st.error(f"Could not write the explanation: {e}")
                    st.info("Fix: copy .env.example to .env, paste your free Gemini API key from Google AI Studio into it, then restart Streamlit.")

st.divider()
st.caption(f"Always check the printed label. Unsure? Call {HELPLINE} or ask your local agriculture officer / Krishi Vigyan Kendra.")
