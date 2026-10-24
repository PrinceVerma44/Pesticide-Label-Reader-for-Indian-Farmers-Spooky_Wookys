# India's CIB&RC colour code printed on every pesticide label.
TOXICITY = {
    "red": ("🔴", "Extremely toxic"),
    "yellow": ("🟡", "Highly toxic"),
    "blue": ("🔵", "Moderately toxic"),
    "green": ("🟢", "Slightly toxic"),
}


def describe(color):
    if color in TOXICITY:
        icon, text = TOXICITY[color]
        return f"{icon} {text} ({color} label)"
    return "Toxicity colour not found on label"
