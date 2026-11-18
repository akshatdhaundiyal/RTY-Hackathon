"""Deterministic clinical verifier. Pure Python, no I/O besides loading drugs_db.json.

OCR / LLM output is only ever *input* here. Every safety verdict comes from these rules.
Principle: when unsure, never guess and never say "all clear". Return AMBER.
"""
from __future__ import annotations

import calendar
import difflib
import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

DB_PATH = Path(__file__).parent / "drugs_db.json"
DB = json.loads(DB_PATH.read_text(encoding="utf-8"))
BRANDS: dict = DB["brands"]
ALIASES: dict = DB["salt_aliases"]
SALT_CLASSES: dict = DB["salt_classes"]
INTERACTIONS: list = DB["interactions"]
KNOWN_SALTS = {s for b in BRANDS.values() for s, _ in b["salts"]}


# ---------- schemas ----------
def _num(v):
    """Tolerate LLM output like "500mg", "5 days", 0 or "": a number, or None when unknown."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) or None
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return (float(m.group()) or None) if m else None


class PrescribedDrug(BaseModel):
    name: str
    strength_mg: Optional[float] = None
    frequency: Optional[str] = None  # "1-0-1", "BD", "at night"...
    duration_days: Optional[int] = None

    @field_validator("strength_mg", mode="before")
    @classmethod
    def _strength(cls, v):
        return _num(v)

    @field_validator("duration_days", mode="before")
    @classmethod
    def _days(cls, v):
        n = _num(v)
        return int(n) if n else None


class PhysicalStrip(BaseModel):
    name: str
    strength_mg: Optional[float] = None
    expiry: Optional[str] = None  # "03/2027" or "Mar-27"
    batch: Optional[str] = None

    @field_validator("strength_mg", mode="before")
    @classmethod
    def _strength(cls, v):
        return _num(v)


class Finding(BaseModel):
    code: str
    severity: str  # RED | AMBER | GREEN
    title: str
    message_en: str
    message_hi: str
    drugs: list[str] = Field(default_factory=list)


class Resolved(BaseModel):
    input_name: str
    brand: Optional[str]  # canonical DB key, None if unrecognised or generic
    salts: list[str]
    strength_mg: Optional[float]  # printed strength


class Report(BaseModel):
    status: str
    findings: list[Finding]
    schedule: dict[str, list[str]]
    prescribed: list[Resolved]
    strips: list[Resolved]
    summary_en: str
    summary_hi: str


def _amber(code: str, title: str, en: str, hi: str, drugs: Optional[list[str]] = None) -> Finding:
    return Finding(code=code, severity="AMBER", title=title, message_en=en, message_hi=hi, drugs=drugs or [])


# ---------- name resolution (strict: never map to a different product or strength) ----------
_UNIT = re.compile(r"(\d)\s*(?:mg|mcg|µg|ug|g|ml)\b", re.I)  # "5mg" -> "5 "
_NOISE = re.compile(r"\b(tab|tabs|tablet|tablets|cap|caps|capsule|capsules|ip|mg)\b\.?", re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _norm(name: str) -> str:
    s = _UNIT.sub(r"\1 ", name.lower())
    s = _NOISE.sub(" ", s)
    s = re.sub(r"[^a-z0-9.\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _alpha(s: str) -> str:
    return "".join(re.findall(r"[a-z]+", s))


def canon_salt(s: str) -> str:
    s = _norm(s)
    return ALIASES.get(s, s)


def _key_info(key: str):
    salts = BRANDS[key]["salts"]
    nums = [float(x) for x in _NUM.findall(key)]
    printed = nums[-1] if nums else salts[0][1]
    allowed = set(nums) | {float(mg) for _, mg in salts}
    return _alpha(key), printed, allowed


_INFO = {k: _key_info(k) for k in BRANDS}
_BY_JOINED: dict[str, list[str]] = {}
for _k, (_j, _, _) in _INFO.items():
    _BY_JOINED.setdefault(_j, []).append(_k)


def _fuzzy_joined(ja: str) -> Optional[str]:
    best, score = None, 0.0
    for j in _BY_JOINED:
        if abs(len(j) - len(ja)) > 2:
            continue
        r = difflib.SequenceMatcher(None, ja, j).ratio()
        if (r >= 0.85 or (r >= 0.75 and len(j) == len(ja))) and r > score:
            best, score = j, r
    return best


def resolve(name: str, strength_mg: Optional[float] = None) -> Resolved:
    """Map a printed/handwritten name to a known brand or generic salt.

    OCR typos in the *name* are tolerated. A strength that does not exist for the matched
    brand (Telma 80, Pan 20) makes the item unrecognised instead of silently becoming another dose.
    """
    n = _norm(name)
    nums = [float(x) for x in _NUM.findall(n)]
    wanted = float(strength_mg) if strength_mg else (nums[0] if nums else None)
    ja = _alpha(n)
    unresolved = Resolved(input_name=name, brand=None, salts=[], strength_mg=wanted)

    variants = [ja] + [ja[len(p):] for p in ("tablet", "tab", "cap") if ja.startswith(p) and len(ja) > len(p) + 2]
    joined = next((v for v in variants if v in _BY_JOINED), None)
    if joined is None:
        joined = next((j for j in (_fuzzy_joined(v) for v in variants) if j), None)

    if joined is not None:
        cands = list(_BY_JOINED[joined])
        if wanted is not None:
            cands = [k for k in cands if any(abs(wanted - a) < 1e-9 for a in _INFO[k][2])]
            if not cands:
                return unresolved
            cands.sort(key=lambda k: abs(_INFO[k][1] - wanted))
            key = cands[0]
        elif len(cands) == 1:
            key = cands[0]
        elif len({tuple(s for s, _ in BRANDS[k]["salts"]) for k in cands}) == 1:  # same salts, strength unknown
            return Resolved(input_name=name, brand=None, salts=[s for s, _ in BRANDS[cands[0]]["salts"]], strength_mg=None)
        else:
            return unresolved
        return Resolved(input_name=name, brand=key, salts=[s for s, _ in BRANDS[key]["salts"]], strength_mg=_INFO[key][1])

    # generic salt name, e.g. "Paracetamol 500mg", "Warfarin 5mg"
    salt = canon_salt(" ".join(re.findall(r"[a-z]+", n)))
    if salt not in KNOWN_SALTS:
        m = difflib.get_close_matches(salt, KNOWN_SALTS, n=1, cutoff=0.85)
        salt = m[0] if m else salt
    if salt in KNOWN_SALTS:
        return Resolved(input_name=name, brand=None, salts=[salt], strength_mg=wanted)
    return unresolved


# ---------- expiry ----------
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_NUM_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[/\-.]\s*(\d{4}|\d{2})(?!\d)(?![\s/\-.]*\d)")
_NAME_DATE = re.compile(r"\b([a-z]{3})[a-z]*[\s\-/.,']*(\d{4}|\d{2})(?!\d)(?![\s/\-.,]*\d)")
_MFG = re.compile(r"(mfg|mfd|manuf\w*|b\.?\s*no|batch|lot)\W*$")
_EXP = re.compile(r"(exp\w*|use\s*before|best\s*before)\W*$")


def _eom(mo: int, yr: int) -> Optional[date]:
    if yr < 100:
        yr += 2000
    if not 1 <= mo <= 12:
        return None
    return date(yr, mo, calendar.monthrange(yr, mo)[1])


def parse_expiry(text: str) -> Optional[date]:
    """Return the LAST day of the printed EXPIRY month, or None when it cannot be read with certainty.

    Dates labelled MFG/batch are ignored; a date labelled EXP wins; several unlabelled different
    dates are ambiguous, so None (the caller raises AMBER).
    """
    t = text.strip().lower()
    found: list[tuple[Optional[date], int]] = []  # (date, position in text)
    for m in _NUM_DATE.finditer(t):
        found.append((_eom(int(m.group(1)), int(m.group(2))), m.start()))
    for m in _NAME_DATE.finditer(t):
        if m.group(1) in _MONTHS:
            found.append((_eom(_MONTHS[m.group(1)], int(m.group(2))), m.start()))
    cands = []
    for d, pos in found:
        if d is None:
            continue
        before = t[max(0, pos - 14):pos]
        if _MFG.search(before):
            continue
        cands.append((d, bool(_EXP.search(before))))
    if not cands:
        return None
    labelled = [d for d, e in cands if e]
    if labelled:
        return max(labelled)
    dates = {d for d, _ in cands}
    return dates.pop() if len(dates) == 1 else None


# ---------- schedule ----------
_SLOTS = ("morning", "afternoon", "night")


_DOSE = r"[0-9]+(?:\s*/\s*[0-9]+)?(?:\.[0-9]+)?|½|¼"  # 1, 0, 1/2, 0.5
_PATTERN = re.compile(rf"(?<![\d/.])((?:{_DOSE})(?:\s*-\s*(?:{_DOSE})){{2,3}})(?![\d/.])")  # tolerates "1-0-1x"
_NOT_FREQUENCY = re.compile(r"\b(after|before|with)\s+(food|meals?|water|milk)\b")
_NOT_DAILY = re.compile(r"\b(week|weekly|alternate|alt\.?\s*day|every other|sos|prn|as needed|if needed|when needed|monthly)\b")
_WORDS = {
    "morning": r"\b(morning|am|breakfast)\b",
    "afternoon": r"\b(afternoon|noon|lunch)\b",
    "night": r"\b(night|bedtime|hs|evening|dinner)\b",
}


def parse_schedule(freq: Optional[str]) -> tuple[list[str], bool]:
    """Return (slots, clear). clear=False means a frequency was written that we cannot turn into a
    daily schedule (weekly, SOS, 4 times a day, 0-0-0, gibberish): the caller raises AMBER."""
    if not freq or not freq.strip():
        return [], True
    f = _NOT_FREQUENCY.sub(" ", freq.lower()).strip(" ,;.")
    if not f:  # only food instructions: nothing to schedule, nothing wrong
        return [], True
    if _NOT_DAILY.search(f):
        return [], False
    m = _PATTERN.search(f)
    if m:  # 1-0-1, 1-0-0-1 (morning, afternoon, evening, night), 1/2-0-1/2
        parts = [re.sub(r"\s+", "", p) for p in re.split(r"\s*-\s*", m.group(1))]
        on = [p not in ("0", "0.0") for p in parts]
        slots = {"morning": on[0], "afternoon": on[1], "night": on[-1]}
        if len(on) == 4:
            slots["afternoon"] = on[1] or on[2]
        out = [s for s in _SLOTS if slots[s]]
        return out, bool(out)
    found = [s for s in _SLOTS if re.search(_WORDS[s], f)]
    if found:
        return found, True
    if re.search(r"\b(tds|tid|thrice|three times|q\s?8\s?h|every\s+8\s+hours?)\b", f):
        return list(_SLOTS), True
    if re.search(r"\b(bd|bid|twice|q\s?12\s?h|every\s+12\s+hours?)\b", f):
        return ["morning", "night"], True
    if re.search(r"\b(od|once|daily|q\s?24\s?h)\b", f):
        return ["morning"], True
    return [], False  # QID, q6h, unreadable...


def parse_frequency(freq: Optional[str]) -> list[str]:
    return parse_schedule(freq)[0]


# ---------- grounding: compare extracted entities with what the OCR text actually shows ----------
_TERMS: dict[str, str] = {}
for _key in BRANDS:
    _w = re.findall(r"[a-z]+", _key)[0]
    if len(_w) >= 4:
        _TERMS[_w] = "brand"
for _s in KNOWN_SALTS:
    _TERMS[_s] = "salt"


SIDE_HI = {"prescription": "पर्चे की फ़ोटो", "medicine strips": "दवा की स्ट्रिप की फ़ोटो"}


def mentioned_terms(text: str) -> set[str]:
    t = text.lower()
    return {term for term in _TERMS if re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", t)}


def grounding_findings(raw_text: str, resolved: list[Resolved], side: str) -> list[Finding]:
    """AMBER when a known medicine name appears in the image text but was not extracted,
    or an extracted name is nowhere in the image text. Catches LLM omissions and prompt injection."""
    out: list[Finding] = []
    side_hi = SIDE_HI.get(side, side)
    covered = set()
    for r in resolved:
        covered.update(r.salts)
        if r.brand:
            covered.add(re.findall(r"[a-z]+", r.brand)[0])
        covered.update(re.findall(r"[a-z]+", r.input_name.lower()))
        covered.add(_alpha(r.input_name.lower()))
    for term in sorted(mentioned_terms(raw_text) - covered):
        out.append(_amber(
            "UNEXTRACTED_MEDICINE", f"'{term.title()}' seen in the {side} but not read",
            f"The text of the {side} mentions '{term}' but it was not read as a medicine. Check it by eye.",
            f"{side_hi} में '{term}' लिखा दिख रहा है, पर इसे दवा के रूप में नहीं पढ़ा गया। कृपया खुद देखकर जांच लें।", [term.title()]))
    compact = _alpha(raw_text.lower())
    for r in resolved:
        first = re.findall(r"[a-z]+", _norm(r.input_name))
        first = next((w for w in first if len(w) >= 4), None)
        if first and first not in compact:
            out.append(_amber(
                "UNGROUNDED_ENTRY", f"'{r.input_name}' not found in the {side} text",
                f"'{r.input_name}' was extracted but does not appear in the {side} text. Check it by eye.",
                f"'{r.input_name}' पढ़ी गई, लेकिन यह {side_hi} में नहीं मिली। कृपया खुद देखकर जांच लें।", [r.input_name]))
    return out


# ---------- checks ----------
def _tokens(r: Resolved) -> set[str]:
    t = set(r.salts)
    for s in r.salts:
        t.update(SALT_CLASSES.get(s, []))
    return t


_ACRONYMS = {"Dsr": "DSR", "Av": "AV"}


def _label(r: Resolved) -> str:
    """Display name: title case, but keep brand suffixes that are acronyms (Pantocid DSR, Ecosprin AV 75)."""
    return " ".join(_ACRONYMS.get(w, w) for w in (r.brand or r.input_name).title().split(" "))


def _same_strength(a: float, b: float) -> bool:
    return abs(a - b) <= 0.01 * max(a, b)


def analyze(prescribed: list[PrescribedDrug], strips: list[PhysicalStrip], today: Optional[date] = None,
            extra_findings: Optional[list[Finding]] = None) -> Report:
    today = today or date.today()
    findings: list[Finding] = list(extra_findings or [])
    rx = [resolve(p.name, p.strength_mg) for p in prescribed]
    st = [resolve(s.name, s.strength_mg) for s in strips]

    # 0. Nothing to verify, or one side missing: never "all clear".
    if not rx and not st:
        findings.append(_amber("NO_INPUT", "No medicines were read",
                               "No medicines could be read from the images. Retake clearer photos or check by hand.",
                               "फ़ोटो से कोई भी दवा नहीं पढ़ी जा सकी। कृपया साफ़ फ़ोटो लें या खुद जांचें।"))
    elif not st:
        findings.append(_amber("NO_STRIPS", "No medicine strips were read",
                               "No medicine strips could be read, so nothing could be checked against the prescription.",
                               "दवा की कोई स्ट्रिप नहीं पढ़ी जा सकी, इसलिए पर्चे से मिलान नहीं हो सका।"))
    elif not rx:
        findings.append(_amber("NO_PRESCRIPTION", "No prescription was read",
                               "No prescription could be read, so the strips could not be checked against it.",
                               "पर्चे की फ़ोटो पढ़ी नहीं जा सकी, इसलिए दवाओं का मिलान नहीं हो सका।"))

    # 0b. Unrecognised items: never guess.
    for r in rx + st:
        if not r.salts:
            name_disp = r.input_name.strip() or "unrecognised medicine"
            findings.append(_amber(
                "UNRECOGNISED", f"Cannot identify {name_disp}"
                + (f" ({r.strength_mg:g})" if r.strength_mg else ""),
                f"'{name_disp}' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it.",
                f"'{name_disp}' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।", [name_disp]))

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

    # 1b. Same salt written on more than one prescription line.
    rx_by_salt: dict[str, list[int]] = {}
    for i, r in enumerate(rx):
        for s in r.salts:
            rx_by_salt.setdefault(s, []).append(i)
    for salt, idx in rx_by_salt.items():
        if len(idx) > 1:
            names = [_label(rx[i]) for i in idx]
            findings.append(_amber(
                "DUPLICATE_PRESCRIPTION", f"{salt.title()} listed more than once on the prescription",
                f"{' and '.join(names)} both contain {salt} on the prescription. Ask the doctor if this is intended.",
                f"पर्चे में {' और '.join(names)} दोनों में {salt} है। डॉक्टर से पूछें कि क्या यह सही है।", names))

    # 2. Match prescription lines to strips (each strip serves one line); dosage mismatch; extras.
    assigned: set[int] = set()
    for pr in rx:
        if not pr.salts:
            continue
        exact = [i for i, sr in enumerate(st) if set(sr.salts) == set(pr.salts)]
        free = [i for i in exact if i not in assigned]
        if free:
            def _family(r: Resolved) -> str:
                return re.findall(r"[a-z]+", r.brand)[0] if r.brand else _alpha(_norm(r.input_name))

            # prefer the same brand family (Dolo <-> Dolo), then equal strength, then first free strip
            pick = next((i for i in free if _family(st[i]) == _family(pr)),
                        next((i for i in free if pr.strength_mg is None or st[i].strength_mg is None
                              or _same_strength(pr.strength_mg, st[i].strength_mg)), free[0]))
            assigned.add(pick)
            sr = st[pick]
            if pr.strength_mg is not None and sr.strength_mg is not None:
                if not _same_strength(pr.strength_mg, sr.strength_mg):
                    over = sr.strength_mg > pr.strength_mg
                    findings.append(Finding(
                        code="DOSAGE_MISMATCH", severity="RED" if over else "AMBER",
                        title=f"Wrong strength: {_label(sr)}",
                        message_en=f"The doctor prescribed {pr.strength_mg:g} mg but the strip says {sr.strength_mg:g} mg"
                                   f"{' (higher than prescribed)' if over else ' (lower than prescribed)'}. Check with the pharmacist.",
                        message_hi=f"डॉक्टर ने {pr.strength_mg:g} mg लिखी है पर स्ट्रिप पर {sr.strength_mg:g} mg है ({'पर्चे से अधिक मात्रा' if over else 'पर्चे से कम मात्रा'})। फार्मासिस्ट से पूछें।",
                        drugs=[_label(pr), _label(sr)]))
                elif not any(f.code == "DUPLICATE_SALT" and _label(sr) in f.drugs for f in findings):
                    findings.append(Finding(
                        code="MATCH", severity="GREEN", title=f"{_label(sr)} matches prescription",
                        message_en=f"{_label(sr)} matches the prescription.",
                        message_hi=f"{_label(sr)} पर्चे से मेल खाती है।", drugs=[_label(sr)]))
            else:
                findings.append(_amber(
                    "STRENGTH_UNVERIFIED", f"Strength not verified: {_label(sr)}",
                    f"The strength of {_label(sr)} could not be compared with the prescription. Check it by eye.",
                    f"{_label(sr)} की मात्रा पर्चे से मिलाई नहीं जा सकी। कृपया खुद देखकर जांच लें।", [_label(sr)]))
            continue
        if exact:  # strip already used by another line: covered by DUPLICATE_PRESCRIPTION
            continue
        part = [i for i, sr in enumerate(st) if (set(sr.salts) & set(pr.salts)) and i not in assigned]
        if part:
            sr = st[part[0]]
            assigned.add(part[0])
            findings.append(_amber(
                "SALT_MISMATCH", f"Different contents: {_label(sr)}",
                f"{_label(pr)} is prescribed ({', '.join(pr.salts)}) but the strip {_label(sr)} contains "
                f"{', '.join(sr.salts)}. It is not the same medicine. Check with the pharmacist.",
                f"{_label(pr)} लिखी गई है पर {_label(sr)} में अलग दवाएं ({', '.join(sr.salts)}) हैं। फार्मासिस्ट से पूछें।",
                [_label(pr), _label(sr)]))
        else:
            findings.append(_amber(
                "MISSING_STRIP", f"{_label(pr)} not on the table",
                f"{_label(pr)} is prescribed but no matching strip was found.",
                f"{_label(pr)} लिखी गई है लेकिन उसकी स्ट्रिप नहीं मिली।", [_label(pr)]))
    for i, sr in enumerate(st):
        if i not in assigned and sr.salts and rx:
            findings.append(_amber(
                "NOT_PRESCRIBED", f"{_label(sr)} is not on the prescription",
                f"{_label(sr)} was not prescribed. Do not take it without asking the doctor.",
                f"{_label(sr)} पर्चे में नहीं है। डॉक्टर से पूछे बिना न लें।", [_label(sr)]))

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
                    if a == b and set(di.salts) & set(dj.salts):  # same salt: DUPLICATE_SALT already covers it
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
            findings.append(_amber(
                "EXPIRY_MISSING", f"Expiry not read: {_label(r)}",
                f"The expiry date of {_label(r)} was not read. Check it by eye before taking it.",
                f"{_label(r)} की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले कृपया खुद देखकर जांच लें।", [_label(r)]))
            continue
        d = parse_expiry(s.expiry)
        if d is None:
            findings.append(_amber(
                "EXPIRY_UNREADABLE", f"Check expiry: {_label(r)}",
                f"Could not read the expiry date '{s.expiry}' on {_label(r)}. Check it by eye.",
                f"{_label(r)} की एक्सपायरी तारीख '{s.expiry}' पढ़ी नहीं जा सकी। कृपया खुद देखकर जांच लें।", [_label(r)]))
        elif d < today:
            findings.append(Finding(
                code="EXPIRED_BATCH", severity="RED", title=f"Expired: {_label(r)}",
                message_en=f"{_label(r)} expired on {d:%d %b %Y}. Do not take it. Throw it away safely.",
                message_hi=f"{_label(r)} की एक्सपायरी तारीख ({d:%d/%m/%Y}) बीत चुकी है। इसे बिल्कुल न खाएं।", drugs=[_label(r)]))

    # 5. Daily schedule from the prescription; a written timing we cannot read is flagged, not dropped.
    schedule: dict[str, list[str]] = {s: [] for s in _SLOTS}
    for p, pr in zip(prescribed, rx):
        slots, clear = parse_schedule(p.frequency)
        for slot in slots:
            schedule[slot].append(_label(pr) if pr.brand else p.name)
        if not clear:
            findings.append(_amber(
                "SCHEDULE_UNCLEAR", f"When to take {_label(pr)} is unclear",
                f"The timing written for {_label(pr)} ('{p.frequency}') could not be turned into a daily schedule. Ask the doctor or pharmacist when to take it.",
                f"{_label(pr)} के लिए लिखा समय ('{p.frequency}') रोज़ के कार्यक्रम में नहीं बदला जा सका। डॉक्टर या फार्मासिस्ट से पूछें कि कब लेनी है।",
                [_label(pr)]))

    # Never GREEN unless at least one medicine was actually verified against the prescription.
    if not any(f.severity != "GREEN" for f in findings) and not any(f.code == "MATCH" for f in findings):
        findings.append(_amber("NOTHING_VERIFIED", "Nothing could be verified",
                               "No medicine could be verified against the prescription. Check by hand.",
                               "पर्चे से किसी भी दवा का मिलान नहीं हो सका। कृपया खुद जांचें।"))

    order = {"RED": 0, "AMBER": 1, "GREEN": 2}
    findings.sort(key=lambda f: order[f.severity])
    status = "RED" if any(f.severity == "RED" for f in findings) else ("AMBER" if any(f.severity == "AMBER" for f in findings) else "GREEN")

    bad =[f for f in findings if f.severity != "GREEN"]
    if not bad:
        en = "All clear. Your medicines match the prescription."
        hi = "सब ठीक है। आपकी दवाएं पर्चे से मेल खाती हैं।"
    else:
        en = f"Warning. {len(bad)} problem{'s' if len(bad) > 1 else ''} found. " + " ".join(f.message_en for f in bad)
        hi = (f"सावधान। {len(bad)} {'समस्या मिली है' if len(bad) == 1 else 'समस्याएं मिली हैं'}। "
              + " ".join(f.message_hi for f in bad))
    return Report(status=status, findings=findings, schedule=schedule, prescribed=rx, strips=st,
                  summary_en=en, summary_hi=hi)
