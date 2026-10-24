SOILS = {
    "sandy": "Sandy / light soil",
    "red": "Red soil",
    "black": "Black cotton (regur) soil",
    "alluvial": "Alluvial / loamy soil",
    "laterite": "Laterite soil",
    "clay": "Heavy clay soil",
}

GENERAL = {
    "sandy": [
        "Water drains fast here, so chemicals can wash down toward groundwater. Keep well away from wells and borewells.",
        "Some products can hurt the crop more on light soil. Never go above the label dose.",
    ],
    "red": [
        "Red soil is often low in organic matter, so chemicals stick to it less. Follow the label dose exactly.",
    ],
    "black": [
        "In dry spells this soil cracks and chemicals can move down the cracks quickly.",
        "After heavy rain it holds water and can run off. Avoid spraying just before rain.",
    ],
    "alluvial": [
        "Loamy soil is fairly balanced. Follow the label dose and keep away from water sources.",
    ],
    "laterite": [
        "This soil is porous and chemicals can wash through, like sandy soil. Keep away from wells and streams.",
    ],
    "clay": [
        "Heavy clay holds chemicals longer, and runs off when waterlogged. Do not spray before heavy rain.",
    ],
}

SOIL_ACTING = (
    "This product works through the soil, so the right dose can change with soil type. "
    "Look for a light-soil or heavy-soil dose on the label, or ask the agriculture officer."
)
FOLIAR = "This is sprayed on leaves, so soil type matters less. Still avoid spraying before rain."


def soil_cautions(soil_key, pesticide_type=None, application_method=None):
    notes = list(GENERAL.get(soil_key, []))
    if application_method == "soil application" or pesticide_type == "herbicide":
        notes.append(SOIL_ACTING)
    elif application_method == "foliar spray":
        notes.append(FOLIAR)
    return notes
