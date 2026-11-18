import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safety_engine import PhysicalStrip as S, PrescribedDrug as P, analyze, parse_expiry, parse_frequency, resolve

TODAY = date(2026, 11, 18)


def codes(r):
    return {f.code for f in r.findings}


def test_safe_match():
    r = analyze([P(name="Dolo 650", frequency="1-0-1"), P(name="Telma 40", frequency="1-0-0")],
                [S(name="Dolo 650", expiry="03/2028"), S(name="Telma 40", expiry="Dec-27")], TODAY)
    assert r.status == "GREEN"
    assert r.schedule["morning"] == ["Dolo 650", "Telma 40"] and r.schedule["night"] == ["Dolo 650"]


def test_duplicate_salt():
    r = analyze([P(name="Dolo 650")], [S(name="Dolo 650"), S(name="Crocin 500")], TODAY)
    assert "DUPLICATE_SALT" in codes(r) and r.status == "RED"


def test_duplicate_via_combo():
    r = analyze([], [S(name="Combiflam"), S(name="Dolo 650")], TODAY)
    assert "DUPLICATE_SALT" in codes(r)


def test_dosage_mismatch():
    r = analyze([P(name="Paracetamol", strength_mg=500)], [S(name="Dolo 650")], TODAY)
    f = [f for f in r.findings if f.code == "DOSAGE_MISMATCH"]
    assert f and f[0].severity == "RED"


def test_interaction_nsaid_aspirin():
    r = analyze([], [S(name="Brufen 400"), S(name="Ecosprin 75")], TODAY)
    assert "DRUG_INTERACTION" in codes(r) and r.status == "RED"


def test_interaction_nsaid_warfarin():
    r = analyze([], [S(name="Voveran 50"), S(name="Warf 5")], TODAY)
    assert "DRUG_INTERACTION" in codes(r)


def test_expired_and_formats():
    assert parse_expiry("EXP 03/2025") == date(2025, 3, 31)
    assert parse_expiry("Mar-25") == date(2025, 3, 31)
    assert parse_expiry("Feb 2028") == date(2028, 2, 29)
    r = analyze([], [S(name="Dolo 650", expiry="10/2026"), S(name="Telma 40", expiry="11/2026")], TODAY)
    exp = [f for f in r.findings if f.code == "EXPIRED_BATCH"]
    assert len(exp) == 1 and "Dolo" in exp[0].title  # Nov 2026 is still valid on 18 Nov


def test_fuzzy_ocr_and_unknown():
    assert resolve("Dclo 650").brand == "dolo 650"
    assert resolve("Pantocid DSR").salts == ["pantoprazole", "domperidone"]
    r = analyze([], [S(name="Zzqx Forte")], TODAY)
    assert "UNRECOGNISED" in codes(r)


def test_frequency():
    assert parse_frequency("1-0-1") == ["morning", "night"]
    assert parse_frequency("TDS") == ["morning", "afternoon", "night"]
    assert parse_frequency("at night") == ["night"]
