"""Generate synthetic demo images + seeded scenario JSON. Run: python fixtures/make_fixtures.py"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent


def font(size, bold=False):
    for name in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def prescription(path, doctor, patient, drugs):
    img = Image.new("RGB", (900, 220 + 90 * len(drugs)), "#fdfcf5")
    d = ImageDraw.Draw(img)
    d.text((40, 30), f"{doctor}", font=font(34, True), fill="#123")
    d.text((40, 75), "MBBS, MD (Medicine)  Reg. No. 48213  |  Clinic: Green Park, New Delhi", font=font(20), fill="#345")
    d.line((40, 115, 860, 115), fill="#123", width=3)
    d.text((40, 130), f"Patient: {patient}      Age: 72 / M      Date: 18/11/2026", font=font(24), fill="#111")
    y = 190
    for i, (name, freq, days) in enumerate(drugs, 1):
        d.text((50, y), f"{i}. {name}", font=font(34, True), fill="#111")
        d.text((120, y + 42), f"{freq}   x {days} days", font=font(24), fill="#333")
        y += 90
    img.save(path)


def strips(path, items):
    cols, w, h = 2, 440, 230
    rows = (len(items) + 1) // 2
    img = Image.new("RGB", (cols * w + 40, rows * h + 40), "#c9ced6")
    d = ImageDraw.Draw(img)
    for i, (brand, strength, salt, exp, batch) in enumerate(items):
        x, y = 20 + (i % cols) * w, 20 + (i // cols) * h
        d.rounded_rectangle((x, y, x + w - 20, y + h - 20), 14, fill="#e8eaee", outline="#8a929e", width=3)
        d.text((x + 20, y + 14), f"{brand} {strength}", font=font(44, True), fill="#0b3d91")
        d.text((x + 20, y + 76), f"Each tablet contains: {salt}", font=font(19), fill="#222")
        d.text((x + 20, y + 112), "Tablets  |  Strip of 10", font=font(19), fill="#222")
        d.text((x + 20, y + 150), f"B.No: {batch}   EXP: {exp}", font=font(24, True), fill="#7a0000")
    img.save(path)


# Scenario 2: hidden duplicate salt (Dolo + Crocin), NSAID + aspirin (Brufen + Ecosprin),
# wrong strength (Rx Dolo 500 vs strip 650) and an expired strip (Crocin 05/2026).
prescription(OUT / "rx_sample.png", "Dr. R. K. Mehta", "Ramesh Kumar",
             [("Tab Dolo 500", "1-0-1", 5), ("Tab Pantocid DSR", "1-0-0", 10), ("Tab Ecosprin 75", "0-0-1", 30)])
strips(OUT / "strips_mismatch.png", [
    ("Dolo", "650", "Paracetamol IP 650 mg", "08/2027", "DL4410"),
    ("Crocin", "500", "Paracetamol IP 500 mg", "05/2026", "CR2087"),
    ("Brufen", "400", "Ibuprofen IP 400 mg", "12/2027", "BR9931"),
    ("Ecosprin", "75", "Aspirin IP 75 mg", "10/2027", "EC1175"),
    ("Pantocid DSR", "", "Pantoprazole 40 mg + Domperidone 30 mg", "09/2027", "PN3320"),
])
# Scenario 1: safe match.
prescription(OUT / "rx_safe.png", "Dr. S. Iyer", "Sunita Devi",
             [("Tab Dolo 650", "1-0-1", 5), ("Tab Telma 40", "1-0-0", 30), ("Tab Pantocid DSR", "1-0-0", 10)])
strips(OUT / "strips_safe.png", [
    ("Dolo", "650", "Paracetamol IP 650 mg", "08/2027", "DL5521"),
    ("Telma", "40", "Telmisartan IP 40 mg", "03/2028", "TM8802"),
    ("Pantocid DSR", "", "Pantoprazole 40 mg + Domperidone 30 mg", "09/2027", "PN4410"),
])

scenarios = {
    "safe": {
        "title": "Scenario 1: Safe Match",
        "rx_image": "rx_safe.png", "strips_image": "strips_safe.png",
        "prescribed": [
            {"name": "Dolo", "strength_mg": 650, "frequency": "1-0-1", "duration_days": 5},
            {"name": "Telma", "strength_mg": 40, "frequency": "1-0-0", "duration_days": 30},
            {"name": "Pantocid DSR", "strength_mg": None, "frequency": "1-0-0", "duration_days": 10}],
        "strips": [
            {"name": "Dolo", "strength_mg": 650, "expiry": "08/2027", "batch": "DL5521"},
            {"name": "Telma", "strength_mg": 40, "expiry": "03/2028", "batch": "TM8802"},
            {"name": "Pantocid DSR", "strength_mg": None, "expiry": "09/2027", "batch": "PN4410"}],
    },
    "trap": {
        "title": "Scenario 2: Hidden Duplicate Salt + Interaction Trap",
        "rx_image": "rx_sample.png", "strips_image": "strips_mismatch.png",
        "prescribed": [
            {"name": "Dolo", "strength_mg": 500, "frequency": "1-0-1", "duration_days": 5},
            {"name": "Pantocid DSR", "strength_mg": None, "frequency": "1-0-0", "duration_days": 10},
            {"name": "Ecosprin", "strength_mg": 75, "frequency": "0-0-1", "duration_days": 30}],
        "strips": [
            {"name": "Dolo", "strength_mg": 650, "expiry": "08/2027", "batch": "DL4410"},
            {"name": "Crocin", "strength_mg": 500, "expiry": "05/2026", "batch": "CR2087"},
            {"name": "Brufen", "strength_mg": 400, "expiry": "12/2027", "batch": "BR9931"},
            {"name": "Ecosprin", "strength_mg": 75, "expiry": "10/2027", "batch": "EC1175"},
            {"name": "Pantocid DSR", "strength_mg": None, "expiry": "09/2027", "batch": "PN3320"}],
    },
}
(OUT / "scenarios.json").write_text(json.dumps(scenarios, indent=2), encoding="utf-8")
print("fixtures written to", OUT)


# Single-medicine prescription for the real Dolo-650 strip photos (fixtures/real/dolo650.jpeg, camera photos):
# matches a Dolo 650 strip, so the result is a MATCH (expiry may still need checking by eye).
prescription(OUT / "rx_dolo650.png", "Dr. A. Sharma", "Ramesh Kumar",
             [("Tab Dolo 650", "1-0-1", 5)])
print("rx_dolo650.png written")
