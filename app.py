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
    if en in HEADINGS and language_value in HEADINGS[en]:
        return HEADINGS[en][language_value]
    if language_value == "Hindi" and hi:
        return hi
    if language_value == "Marathi" and mr:
        return mr
    return en


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
    if text in KNOWN_TEXT and language_value in KNOWN_TEXT[text]:
        return KNOWN_TEXT[text][language_value]
    if text in SOIL_EXTENDED and language_value in SOIL_EXTENDED[text]:
        return SOIL_EXTENDED[text][language_value]
    return text


UI_STRINGS = {
    "Mix in one": {"Hindi": "एक में मिलाएँ", "Marathi": "एका मध्ये मिसळा", "Gujarati": "એકમાં ભેળવો", "Tamil": "ஒன்றில் கலக்கவும்", "Telugu": "ఒకదానిలో కలపండి", "Kannada": "ಒಂದರಲ್ಲಿ ಬೆರೆಸಿ", "Bengali": "একটিতে মেশান", "Punjabi": "ਇੱਕ ਵਿੱਚ ਮਿਲਾਓ"},
    "tank": {"Hindi": "टंकी", "Marathi": "टाकी", "Gujarati": "ટાંકી", "Tamil": "தொட்டி", "Telugu": "ట్యాంకు", "Kannada": "ಟ್ಯಾಂಕ್", "Bengali": "ট্যাঙ্ক", "Punjabi": "ਟੈਂਕੀ"},
    "Working": {"Hindi": "हिसाब", "Marathi": "हिशोब", "Gujarati": "ગણતરી", "Tamil": "கணக்கு", "Telugu": "లెక్క", "Kannada": "ಲೆಕ್ಕ", "Bengali": "হিসাব", "Punjabi": "ਹਿਸਾਬ"},
    "One tank covers about": {"Hindi": "एक टंकी लगभग", "Marathi": "एक टाकी सुमारे", "Gujarati": "એક ટાંકી લગભગ", "Tamil": "ஒரு தொட்டி சுமார்", "Telugu": "ఒక ట్యాంకు సుమారు", "Kannada": "ಒಂದು ಟ್ಯಾಂಕ್ ಸುಮಾರು", "Bengali": "একটি ট্যাঙ্ক প্রায়", "Punjabi": "ਇੱਕ ਟੈਂਕੀ ਲਗਭਗ"},
    "acre": {"Hindi": "एकड़", "Marathi": "एकर", "Gujarati": "એકર", "Tamil": "ஏக்கர்", "Telugu": "ఎకరం", "Kannada": "ಎಕರೆ", "Bengali": "একর", "Punjabi": "ਏਕੜ"},
    "Spray": {"Hindi": "छिड़काव", "Marathi": "फवारणी", "Gujarati": "છંટકાવ", "Tamil": "தெளிப்பு", "Telugu": "పిచికారీ", "Kannada": "ಸಿಂಪಡಣೆ", "Bengali": "স্প্রে", "Punjabi": "ਸਪਰੇਅ"},
    "Wait": {"Hindi": "प्रतीक्षा", "Marathi": "प्रतीक्षा", "Gujarati": "રાહ જુઓ", "Tamil": "காத்திருங்கள்", "Telugu": "వేచి ఉండండి", "Kannada": "ಕಾಯಿರಿ", "Bengali": "অপেক্ষা", "Punjabi": "ਉਡੀਕ"},
    "Harvest from": {"Hindi": "कटाई से", "Marathi": "कापणी पासून", "Gujarati": "કાપણીથી", "Tamil": "அறுவடை முதல்", "Telugu": "కోత నుండి", "Kannada": "ಕೊಯ್ಲಿನಿಂದ", "Bengali": "কাটা থেকে", "Punjabi": "ਵਾਢੀ ਤੋਂ"},
    "days": {"Hindi": "दिन", "Marathi": "दिवस", "Gujarati": "દિવસ", "Tamil": "நாட்கள்", "Telugu": "రోజులు", "Kannada": "ದಿನಗಳು", "Bengali": "দিন", "Punjabi": "ਦਿਨ"},
    "Safety ready": {"Hindi": "सुरक्षा तैयार", "Marathi": "सुरक्षा तयार", "Gujarati": "સલામતી તૈયાર", "Tamil": "பாதுகாப்பு தயார்", "Telugu": "భద్రత సిద్ధం", "Kannada": "ಸುರಕ್ಷತೆ ಸಿದ್ಧ", "Bengali": "নিরাপত্তা প্রস্তুত", "Punjabi": "ਸੁਰੱਖਿਆ ਤਿਆਰ"},
    "ticked": {"Hindi": "टिक किए गए", "Marathi": "टिक केलेले", "Gujarati": "ટિક કરેલા", "Tamil": "டிக் செய்யப்பட்டது", "Telugu": "టిక్ చేసినవి", "Kannada": "ಟಿಕ್ ಮಾಡಲಾಗಿದೆ", "Bengali": "টিক দেওয়া", "Punjabi": "ਟਿਕ ਲਗਾਏ"},
    "All safety steps ticked. Still follow the printed label.": {"Hindi": "सभी सुरक्षा कदम टिक कर दिए गए। फिर भी छपे लेबल का पालन करें।", "Marathi": "सर्व सुरक्षा पायऱ्या टिक केल्या आहेत. तरीही छापील लेबलचे पालन करा.", "Gujarati": "બધા સલામતી પગલાં ટિક કર્યા છે. છતાં છાપેલા લેબલનું પાલન કરો.", "Tamil": "அனைத்து பாதுகாப்பு படிகளும் டிக் செய்யப்பட்டன. இன்னும் அச்சிடப்பட்ட லேபிளைப் பின்பற்றவும்.", "Telugu": "అన్ని భద్రతా చర్యలు టిక్ చేయబడ్డాయి. అయినా ముద్రించిన లేబుల్‌ను పాటించండి.", "Kannada": "ಎಲ್ಲಾ ಸುರಕ್ಷತಾ ಹಂತಗಳನ್ನು ಟಿಕ್ ಮಾಡಲಾಗಿದೆ. ಆದರೂ ಮುದ್ರಿತ ಲೇಬಲ್ ಅನ್ನು ಅನುಸರಿಸಿ.", "Bengali": "সব নিরাপত্তা ধাপ টিক দেওয়া হয়েছে। তবুও ছাপা লেবেল মেনে চলুন।", "Punjabi": "ਸਾਰੇ ਸੁਰੱਖਿਆ ਕਦਮ ਟਿਕ ਲਗਾਏ ਗਏ ਹਨ। ਫਿਰ ਵੀ ਛਪੇ ਲੇਬਲ ਦੀ ਪਾਲਣਾ ਕਰੋ।"},
    "First aid (from the label)": {"Hindi": "प्राथमिक उपचार (लेबल से)", "Marathi": "प्रथमोपचार (लेबलवरून)", "Gujarati": "પ્રાથમિક સારવાર (લેબલ પરથી)", "Tamil": "முதலுதவி (லேபிளில் இருந்து)", "Telugu": "ప్రథమ చికిత్స (లేబుల్ నుండి)", "Kannada": "ಪ್ರಥಮ ಚಿಕಿತ್ಸೆ (ಲೇಬಲ್‌ನಿಂದ)", "Bengali": "প্রাথমিক চিকিৎসা (লেবেল থেকে)", "Punjabi": "ਮੁੱਢਲੀ ਸਹਾਇਤਾ (ਲੇਬਲ ਤੋਂ)"},
    "Raw data read from the label (for judges)": {"Hindi": "लेबल से पढ़ा गया कच्चा डेटा (जजों के लिए)", "Marathi": "लेबलवरून वाचलेला कच्चा डेटा (परीक्षकांसाठी)", "Gujarati": "લેબલ પરથી વાંચેલો કાચો ડેટા (ન્યાયાધીશો માટે)", "Tamil": "லேபிளில் இருந்து படிக்கப்பட்ட மூல தரவு (நடுவர்களுக்கு)", "Telugu": "లేబుల్ నుండి చదివిన ముడి డేటా (న్యాయనిర్ణేతల కోసం)", "Kannada": "ಲೇಬಲ್‌ನಿಂದ ಓದಲಾದ ಕಚ್ಚಾ ಡೇಟಾ (ನ್ಯಾಯಾಧೀಶರಿಗಾಗಿ)", "Bengali": "লেবেল থেকে পড়া কাঁচা তথ্য (বিচারকদের জন্য)", "Punjabi": "ਲੇਬਲ ਤੋਂ ਪੜ੍ਹਿਆ ਕੱਚਾ ਡਾਟਾ (ਜੱਜਾਂ ਲਈ)"},
    "Explain": {"Hindi": "समझाएँ", "Marathi": "स्पष्टीकरण", "Gujarati": "સમજાવો", "Tamil": "விளக்கவும்", "Telugu": "వివరించండి", "Kannada": "ವಿವರಿಸಿ", "Bengali": "ব্যাখ্যা করুন", "Punjabi": "ਸਮਝਾਓ"},
    "Label wording stays as printed so you can check it against the bottle — the Explain paragraph below translates it in full.": {"Hindi": "लेबल की शब्दावली जैसी छपी है वैसी ही रहती है ताकि आप इसे बोतल से मिला सकें — नीचे का Explain अनुच्छेद इसे पूरा अनुवाद करता है।", "Marathi": "लेबलवरील शब्द जसे छापले आहेत तसेच राहतात, जेणेकरून तुम्ही ते बाटलीशी तपासू शकता — खालील Explain परिच्छेद त्याचा पूर्ण अनुवाद करतो."},
    "Always check the printed label.": {"Hindi": "हमेशा छपे लेबल की जाँच करें।", "Marathi": "नेहमी छापील लेबल तपासा।", "Gujarati": "હંમેશા છાપેલા લેબલની તપાસ કરો.", "Tamil": "எப்போதும் அச்சிடப்பட்ட லேபிளைச் சரிபார்க்கவும்.", "Telugu": "ఎల్లప్పుడూ ముద్రించిన లేబుల్‌ను తనిఖీ చేయండి.", "Kannada": "ಯಾವಾಗಲೂ ಮುದ್ರಿತ ಲೇಬಲ್ ಅನ್ನು ಪರಿಶೀಲಿಸಿ.", "Bengali": "সবসময় ছাপা লেবেল পরীক্ষা করুন।", "Punjabi": "ਹਮੇਸ਼ਾ ਛਪੇ ਲੇਬਲ ਦੀ ਜਾਂਚ ਕਰੋ।"},
    "Unsure? Call": {"Hindi": "शक है? कॉल करें", "Marathi": "शंका आहे? कॉल करा", "Gujarati": "શંકા છે? કૉલ કરો", "Tamil": "சந்தேகமா? அழைக்கவும்", "Telugu": "సందేహమా? కాల్ చేయండి", "Kannada": "ಸಂದೇಹವಿದೆಯೇ? ಕರೆ ಮಾಡಿ", "Bengali": "সন্দেহ? কল করুন", "Punjabi": "ਸ਼ੱਕ ਹੈ? ਕਾਲ ਕਰੋ"},
    "or ask your local agriculture officer / Krishi Vigyan Kendra.": {"Hindi": "या अपने स्थानीय कृषि अधिकारी / कृषि विज्ञान केंद्र से पूछें।", "Marathi": "किंवा तुमच्या स्थानिक कृषी अधिकाऱ्याला / कृषी विज्ञान केंद्राला विचारा।", "Gujarati": "અથવા તમારા સ્થાનિક કૃષિ અધિકારી / કૃષિ વિજ્ઞાન કેન્દ્રને પૂછો.", "Tamil": "அல்லது உங்கள் உள்ளூர் வேளாண் அதிகாரி / கிருஷி விஞ்ஞான் கேந்திராவிடம் கேளுங்கள்.", "Telugu": "లేదా మీ స్థానిక వ్యవసాయ అధికారి / కృషి విజ్ఞాన కేంద్రాన్ని అడగండి.", "Kannada": "ಅಥವಾ ನಿಮ್ಮ ಸ್ಥಳೀಯ ಕೃಷಿ ಅಧಿಕಾರಿ / ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಕೇಳಿ.", "Bengali": "অথবা আপনার স্থানীয় কৃষি আধিকারিক / কৃষি বিজ্ঞান কেন্দ্রকে জিজ্ঞাসা করুন।", "Punjabi": "ਜਾਂ ਆਪਣੇ ਸਥਾਨਕ ਖੇਤੀਬਾੜੀ ਅਧਿਕਾਰੀ / ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ ਨੂੰ ਪੁੱਛੋ।"},
    "Waiting period not found on the label.": {"Hindi": "लेबल पर प्रतीक्षा अवधि नहीं मिली।", "Marathi": "लेबलवर प्रतीक्षा कालावधी सापडला नाही।", "Gujarati": "લેબલ પર રાહ જોવાનો સમયગાળો મળ્યો નથી.", "Tamil": "லேபிளில் காத்திருப்பு காலம் கிடைக்கவில்லை.", "Telugu": "లేబుల్‌లో వేచి ఉండే కాలం కనిపించలేదు.", "Kannada": "ಲೇಬಲ್‌ನಲ್ಲಿ ಕಾಯುವ ಅವಧಿ ಸಿಗಲಿಲ್ಲ.", "Bengali": "লেবেলে অপেক্ষার সময় পাওয়া যায়নি।", "Punjabi": "ਲੇਬਲ 'ਤੇ ਉਡੀਕ ਸਮਾਂ ਨਹੀਂ ਮਿਲਿਆ।"},
}
SOIL_NAMES = {
    "Sandy / light soil": {"Hindi": "रेतीली / हल्की मिट्टी", "Marathi": "वालुकामय / हलकी माती", "Gujarati": "રેતાળ / હળવી માટી", "Tamil": "மணல் / இலகுவான மண்", "Telugu": "ఇసుక / తేలికపాటి నేల", "Kannada": "ಮರಳು / ಹಗುರವಾದ ಮಣ್ಣು", "Bengali": "বালুকাময় / হালকা মাটি", "Punjabi": "ਰੇਤਲੀ / ਹਲਕੀ ਮਿੱਟੀ"},
    "Red soil": {"Hindi": "लाल मिट्टी", "Marathi": "लाल माती", "Gujarati": "લાલ માટી", "Tamil": "சிவப்பு மண்", "Telugu": "ఎర్ర నేల", "Kannada": "ಕೆಂಪು ಮಣ್ಣು", "Bengali": "লাল মাটি", "Punjabi": "ਲਾਲ ਮਿੱਟੀ"},
    "Black cotton soil": {"Hindi": "काली कपास मिट्टी", "Marathi": "काळी कापूस माती", "Gujarati": "કાળી કપાસ માટી", "Tamil": "கருப்பு பருத்தி மண்", "Telugu": "నల్ల పత్తి నేల", "Kannada": "ಕಪ್ಪು ಹತ್ತಿ ಮಣ್ಣು", "Bengali": "কালো তুলো মাটি", "Punjabi": "ਕਾਲੀ ਕਪਾਹ ਮਿੱਟੀ"},
    "Alluvial soil": {"Hindi": "जलोढ़ मिट्टी", "Marathi": "गाळाची माती", "Gujarati": "કાંપની માટી", "Tamil": "வண்டல் மண்", "Telugu": "ఒండ్రు నేల", "Kannada": "ಮೆಕ್ಕಲು ಮಣ್ಣು", "Bengali": "পলি মাটি", "Punjabi": "ਜਲੋਢ ਮਿੱਟੀ"},
    "Laterite soil": {"Hindi": "लैटेराइट मिट्टी", "Marathi": "लॅटेराइट माती", "Gujarati": "લેટેરાઇટ માટી", "Tamil": "லேட்டரைட் மண்", "Telugu": "లేటరైట్ నేల", "Kannada": "ಲ್ಯಾಟರೈಟ್ ಮಣ್ಣು", "Bengali": "ল্যাটেরাইট মাটি", "Punjabi": "ਲੈਟਰਾਈਟ ਮਿੱਟੀ"},
    "Clay soil": {"Hindi": "चिकनी मिट्टी", "Marathi": "चिकण माती", "Gujarati": "ચીકણી માટી", "Tamil": "களிமண்", "Telugu": "బంకమట్టి", "Kannada": "ಜೇಡಿಮಣ್ಣು", "Bengali": "এঁটেল মাটি", "Punjabi": "ਚਿਕਣੀ ਮਿੱਟੀ"},
}
def us(key, language_value):
    return UI_STRINGS.get(key, {}).get(language_value, key)
def soil_display(name, language_value):
    return SOIL_NAMES.get(name, {}).get(language_value, name)

def safe_explain(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        if "client has been closed" in str(e).lower():
            st.session_state.pop("local_client", None)
            return fn(*args)
        raise


try:
    import kisanlabel.client as _client_mod
    import kisanlabel.explain as _explain_mod
    import kisanlabel.extract as _extract_mod

    def _get_persistent_client():
        if "local_client" not in st.session_state:
            st.session_state["local_client"] = _client_mod.get_client()
        return st.session_state["local_client"]

    _explain_mod.get_client = _get_persistent_client
    _extract_mod.get_client = _get_persistent_client
except Exception:
    pass


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

    st.markdown(f"### 🪱 {tr(language, 'Cautions for', 'सावधानियाँ', 'काळजी')} {soil_display(soil_name, language)}")
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


                st.session_state["explanation"] = safe_explain(explain, facts, language)
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
                    st.markdown(safe_explain(explain_recommendation, crop_in, pest_in, soil_name, matches[:5], cautions, language))
                except Exception as e:
                    st.error(f"Could not write the explanation: {e}")
                    st.info("Fix: make sure Ollama is running and gemma3:4b is pulled (ollama pull gemma3:4b), then restart Streamlit. No API key is used.")

st.divider()
st.caption(f"{us('Always check the printed label.', language)} {us('Unsure? Call', language)} {HELPLINE} {us('or ask your local agriculture officer / Krishi Vigyan Kendra.', language)}")
