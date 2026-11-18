"""Deterministic clinical verifier. Pure Python, no I/O besides loading drugs_db.json.

OCR / LLM output is only ever *input* here. Every safety verdict comes from these rules.
"""
from __future__ import annotations

import calendar
import difflib
import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

DB_PATH = Path(__file__).parent / "drugs_db.json"
DB = json.loads(DB_PATH.read_text(encoding="utf-8"))
BRANDS: dict = DB["brands"]
ALIASES: dict = DB["salt_aliases"]
SALT_CLASSES: dict = DB["salt_classes"]
INTERACTIONS: list = DB["interactions"]
KNOWN_SALTS = {s for b in BRANDS.values() for s, _ in b["salts"]}


# ---------- schemas ----------
class PrescribedDrug(BaseModel):
    name: str
    strength_mg: Optional[float] = None
    frequency: Optional[str] = None  # "1-0-1", "BD", "at night"...
    duration_days: Optional[int] = None


class PhysicalStrip(BaseModel):
    name: str
    strength_mg: Optional[float] = None
    expiry: Optional[str] = None  # "03/2027" or "Mar-27"
    batch: Optional[str] = None


class Finding(BaseModel):
    code: str
    severity: str  # RED | AMBER | GREEN
    title: str
    message_en: str
    message_hi: str
    drugs: list[str] = Field(default_factory=list)


class Resolved(BaseModel):
    input_name: str
    brand: Optional[str]  # canonical DB key, None if unrecognised
    salts: list[str]
    strength_mg: Optional[float]  # strength of first salt


class Report(BaseModel):
    status: str
    findings: list[Finding]
    schedule: dict[str, list[str]]
    prescribed: list[Resolved]
    strips: list[Resolved]
    summary_en: str
    summary_hi: str


# ---------- normalisation ----------
_NOISE = re.compile(r"\b(tab|tabs|tablet|tablets|cap|capsule|ip|mg)\b\.?", re.I)


def _norm(name: str) -> str:
    s = _NOISE.sub(" ", name.lower())
    s = re.sub(r"[^a-z0-9\- ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^(tablet|tab|cap)(?=[a-z])", "", s).strip()  # "TabDolo" -> "dolo"


_COMPACT = {k.replace(" ", ""): k for k in BRANDS}


def canon_salt(s: str) -> str:
    s = _norm(s)
    return ALIASES.get(s, s)


def resolve(name: str, strength_mg: Optional[float] = None) -> Resolved:
    """Map a printed/handwritten name to a known brand or generic salt (fuzzy, OCR-tolerant)."""
    n = _norm(name)
    cands = [n]
    if strength_mg:
        cands.append(f"{n} {int(strength_mg) if float(strength_mg).is_integer() else strength_mg}")
    key = None
    for c in cands:
        if c in BRANDS:
            key = c
            break
        if c.replace(" ", "") in _COMPACT:  # OCR dropped spaces: "pantociddsr"
            key = _COMPACT[c.replace(" ", "")]
            break
    if key is None:  # same first word, pick brand whose strength matches
        first = n.split(" ")[0] if n else ""
        same = [k for k in BRANDS if k.split(" ")[0] == first and first]
        if same:
            if strength_mg:
                for k in same:
                    if BRANDS[k]["salts"][0][1] == strength_mg:
                        key = k
                        break
            if key is None and len(same) == 1:
                key = same[0]
    if key is None:
        for c in cands:
            m = difflib.get_close_matches(c, BRANDS.keys(), n=1, cutoff=0.82)
            if m:
                key = m[0]
                break
    if key is not None:
        salts = BRANDS[key]["salts"]
        return Resolved(input_name=name, brand=key, salts=[s for s, _ in salts], strength_mg=salts[0][1])
    # generic salt name, e.g. "Paracetamol 500mg"
    base = re.sub(r"\b\d+(\.\d+)?\b", " ", n).strip()
    salt = canon_salt(base)
    if salt not in KNOWN_SALTS:
        m = difflib.get_close_matches(salt, KNOWN_SALTS, n=1, cutoff=0.85)
        salt = m[0] if m else salt
    if salt in KNOWN_SALTS:
        return Resolved(input_name=name, brand=None, salts=[salt], strength_mg=strength_mg)
    return Resolved(input_name=name, brand=None, salts=[], strength_mg=strength_mg)


# ---------- expiry ----------
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}


def parse_expiry(text: str) -> Optional[date]:
    """Return the LAST day of the printed month (strips are valid through month end)."""
    t = text.strip().lower()
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{4}|\d{2})\b", t)
    if m:
        mo, yr = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"\b([a-z]{3})[a-z]*[\s\-/.,']*(\d{4}|\d{2})\b", t)
        if not m or m.group(1) not in _MONTHS:
            return None
        mo, yr = _MONTHS[m.group(1)], int(m.group(2))
    if yr < 100:
        yr += 2000
    if not 1 <= mo <= 12:
        return None
    return date(yr, mo, calendar.monthrange(yr, mo)[1])


# ---------- schedule ----------
_SLOTS = ("morning", "afternoon", "night")


def parse_frequency(freq: Optional[str]) -> list[str]:
    if not freq:
        return []
    f = freq.lower().strip()
    m = re.search(r"([0-9])\s*-\s*([0-9])\s*-\s*([0-9])", f)
    if m:
        return [s for s, v in zip(_SLOTS, m.groups()) if int(v) > 0]
    if re.search(r"\b(tds|tid|thrice|three times|1-1-1)\b", f) or "qid" in f:
        return list(_SLOTS)
    if re.search(r"\b(bd|bid|twice)\b", f):
        return ["morning", "night"]
    if re.search(r"\b(hs|night|bedtime)\b", f):
        return ["night"]
    if re.search(r"\b(od|once|morning|daily)\b", f):
        return ["morning"]
    return []


# ---------- checks ----------
def _tokens(r: Resolved) -> set[str]:
    t = set(r.salts)
    for s in r.salts:
        t.update(SALT_CLASSES.get(s, []))
    return t


def _label(r: Resolved) -> str:
    return (r.brand or r.input_name).title()


def _same_strength(a: float, b: float) -> bool:
    return abs(a - b) <= 0.01 * max(a, b)


def analyze(prescribed: list[PrescribedDrug], strips: list[PhysicalStrip], today: Optional[date] = None) -> Report:
    today = today or date.today()
    findings: list[Finding] = []
    rx = [resolve(p.name, p.strength_mg) for p in prescribed]
    for r, p in zip(rx, prescribed):  # explicit strength on the Rx overrides DB default
        if p.strength_mg is not None:
            r.strength_mg = p.strength_mg
    st = [resolve(s.name, s.strength_mg) for s in strips]
    for r, s in zip(st, strips):
        if s.strength_mg is not None:
            r.strength_mg = s.strength_mg

    # 0. Unrecognised items: never guess.
    for r in rx + st:
        if not r.salts:
            findings.append(Finding(
                code="UNRECOGNISED", severity="AMBER", title=f"Cannot identify {r.input_name}",
                message_en=f"'{r.input_name}' is not in the medicine database. Ask a pharmacist to check it.",
                message_hi=f"'{r.input_name}' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।",
                drugs=[r.input_name]))

    # 1. Duplicate active salt across different strips.
    by_salt: dict[str, list[int]] = {}
    for i, r in enumerate(st):
        for s in r.salts:
            by_salt.setdefault(s, []).append(i)
    for salt, idx in by_salt.items():
        if len(idx) > 1:
            names = [_label(st[i]) for i in idx]
            findings.append(Finding(
                code="DUPLICATE_SALT", severity="RED", title=f"Duplicate medicine: {salt.title()}",
                message_en=f"{' and '.join(names)} both contain {salt}. Taking both can cause an overdose. Take only one.",
                message_hi=f"{' और '.join(names)} दोनों में {salt} है। दोनों लेने से ओवरडोज़ हो सकता है। केवल एक ही लें।",
                drugs=names))

    # 2. Match prescription to strips; dosage mismatch / not prescribed.
    matched_strips: set[int] = set()
    for p, pr in zip(prescribed, rx):
        if not pr.salts:
            continue
        hit = [i for i, sr in enumerate(st) if set(sr.salts) & set(pr.salts)]
        exact = [i for i in hit if set(st[i].salts) == set(pr.salts)]
        pick = exact[0] if exact else (hit[0] if hit else None)
        if pick is None:
            findings.append(Finding(
                code="MISSING_STRIP", severity="AMBER", title=f"{_label(pr)} not on the table",
                message_en=f"{_label(pr)} is prescribed but no matching strip was found.",
                message_hi=f"{_label(pr)} लिखी गई है लेकिन उसकी स्ट्रिप नहीं मिली।",
                drugs=[_label(pr)]))
            continue
        matched_strips.update(exact or hit)
        sr = st[pick]
        if pr.strength_mg is not None and sr.strength_mg is not None and not _same_strength(pr.strength_mg, sr.strength_mg):
            over = sr.strength_mg > pr.strength_mg
            findings.append(Finding(
                code="DOSAGE_MISMATCH", severity="RED" if over else "AMBER",
                title=f"Wrong strength: {_label(sr)}",
                message_en=f"The doctor prescribed {pr.strength_mg:g} mg but the strip says {sr.strength_mg:g} mg"
                           f"{' (higher than prescribed)' if over else ' (lower than prescribed)'}. Check with the pharmacist.",
                message_hi=f"डॉक्टर ने {pr.strength_mg:g} mg लिखी है पर स्ट्रिप पर {sr.strength_mg:g} mg है। फार्मासिस्ट से पूछें।",
                drugs=[_label(pr), _label(sr)]))
        elif not any(f.code == "DUPLICATE_SALT" and _label(sr) in f.drugs for f in findings):
            findings.append(Finding(
                code="MATCH", severity="GREEN", title=f"{_label(sr)} matches prescription",
                message_en=f"{_label(sr)} matches the prescription.",
                message_hi=f"{_label(sr)} पर्चे से मेल खाती है।", drugs=[_label(sr)]))
    for i, sr in enumerate(st):
        if i not in matched_strips and sr.salts and prescribed:
            findings.append(Finding(
                code="NOT_PRESCRIBED", severity="AMBER", title=f"{_label(sr)} is not on the prescription",
                message_en=f"{_label(sr)} was not prescribed. Do not take it without asking the doctor.",
                message_hi=f"{_label(sr)} पर्चे में नहीं है। डॉक्टर से पूछे बिना न लें।", drugs=[_label(sr)]))

    # 3. Interactions across all distinct drugs (strips + prescribed without a strip).
    drugs = list(st) + [pr for pr in rx if not any(set(pr.salts) & set(s.salts) for s in st)]
    seen: set[tuple] = set()
    for rule in INTERACTIONS:
        a, b = rule["a"], rule["b"]
        for i, di in enumerate(drugs):
            for j, dj in enumerate(drugs):
                if i == j or (a == b and j < i):
                    continue
                if a in _tokens(di) and b in _tokens(dj):
                    if a == b and set(di.salts) == set(dj.salts):
                        continue
                    key = (rule["a"], rule["b"], frozenset((i, j)))
                    if key in seen:
                        continue
                    seen.add(key)
                    names = [_label(di), _label(dj)]
                    findings.append(Finding(
                        code="DRUG_INTERACTION", severity=rule["severity"],
                        title=f"Interaction: {names[0]} + {names[1]}",
                        message_en=f"{names[0]} and {names[1]}: {rule['en']}",
                        message_hi=f"{names[0]} और {names[1]}: {rule['hi']}", drugs=names))

    # 4. Expiry.
    for s, r in zip(strips, st):
        if not s.expiry:
            continue
        d = parse_expiry(s.expiry)
        if d is None:
            findings.append(Finding(
                code="EXPIRY_UNREADABLE", severity="AMBER", title=f"Check expiry: {_label(r)}",
                message_en=f"Could not read the expiry date '{s.expiry}' on {_label(r)}. Check it by eye.",
                message_hi=f"{_label(r)} की एक्सपायरी तारीख '{s.expiry}' पढ़ी नहीं जा सकी। खुद देखें।", drugs=[_label(r)]))
        elif d < today:
            findings.append(Finding(
                code="EXPIRED_BATCH", severity="RED", title=f"Expired: {_label(r)}",
                message_en=f"{_label(r)} expired on {d:%d %b %Y}. Do not take it. Throw it away safely.",
                message_hi=f"{_label(r)} की एक्सपायरी {d:%d/%m/%Y} को खत्म हो चुकी है। इसे न खाएं।", drugs=[_label(r)]))

    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    findings.sort(key=lambda f: order[f.severity])
    status = "RED" if any(f.severity == "RED" for f in findings) else ("AMBER" if any(f.severity == "AMBER" for f in findings) else "GREEN")

    schedule: dict[str, list[str]] = {s: [] for s in _SLOTS}
    for p, pr in zip(prescribed, rx):
        for slot in parse_frequency(p.frequency):
            schedule[slot].append(_label(pr) if pr.brand else p.name)

    bad = [f for f in findings if f.severity != "GREEN"]
    if not bad:
        en = "All clear. Your medicines match the prescription."
        hi = "सब ठीक है। आपकी दवाएं पर्चे से मेल खाती हैं।"
    else:
        en = f"Warning. {len(bad)} problem{'s' if len(bad) > 1 else ''} found. " + " ".join(f.message_en for f in bad)
        hi = f"सावधान। {len(bad)} समस्या मिली। " + " ".join(f.message_hi for f in bad)
    return Report(status=status, findings=findings, schedule=schedule, prescribed=rx, strips=st,
                  summary_en=en, summary_hi=hi)
