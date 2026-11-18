"""Data guards for drugs_db.json plus a broad table of scenarios (engine level, no OCR/LLM)."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safety_engine import BRANDS, INTERACTIONS, KNOWN_SALTS, SALT_CLASSES, PhysicalStrip as S, PrescribedDrug as P, analyze, resolve

TODAY = date(2026, 11, 18)


# ---------- database self-consistency ----------
def test_every_brand_resolves_to_itself():
    bad = [k for k in BRANDS if resolve(k).brand != k]
    assert not bad, f"these brand keys do not resolve to themselves: {bad}"


def test_every_salt_has_a_positive_strength_and_a_name():
    for key, b in BRANDS.items():
        assert b["salts"], key
        for salt, mg in b["salts"]:
            assert salt and mg > 0, (key, salt, mg)


def test_interaction_rules_only_name_known_salts_or_classes():
    classes = {c for cs in SALT_CLASSES.values() for c in cs}
    for r in INTERACTIONS:
        for side in (r["a"], r["b"]):
            assert side in KNOWN_SALTS or side in classes, f"unknown token {side!r} in rule {r['a']}+{r['b']}"
        assert r["severity"] in {"RED", "AMBER"} and r["en"].strip() and r["hi"].strip()


def test_classified_salts_exist_in_the_brand_list():
    assert set(SALT_CLASSES) <= KNOWN_SALTS


def test_database_has_grown_to_a_useful_size():
    assert len(BRANDS) >= 100 and len(INTERACTIONS) >= 20


# ---------- scenario table: (id, prescription, strips) -> expected status and codes ----------
def run(rx, strips):
    return analyze([P(**p) if isinstance(p, dict) else P(name=p) for p in rx],
                   [S(name=s, expiry="03/2028") if isinstance(s, str) else S(**{"expiry": "03/2028", **s}) for s in strips], TODAY)


SCENARIOS = [
    # id, rx, strips, expected status, codes that must appear, codes that must NOT appear
    ("safe_three", ["Dolo 650", "Telma 40", "Pantocid DSR"], ["Dolo 650", "Telma 40", "Pantocid DSR"], "GREEN", {"MATCH"}, {"DUPLICATE_SALT", "DRUG_INTERACTION"}),
    ("paracetamol_two_brands", ["Dolo 650"], ["Dolo 650", "Crocin 650"], "RED", {"DUPLICATE_SALT"}, set()),
    ("paracetamol_three_brands_one_combo", [], ["Dolo 650", "Calpol 500", "Sinarest"], "RED", {"DUPLICATE_SALT"}, set()),
    ("nsaid_plus_aspirin", [], ["Brufen 400", "Ecosprin 75"], "RED", {"DRUG_INTERACTION"}, set()),
    ("combiflam_plus_aspirin", [], ["Combiflam", "Ecosprin 75"], "RED", {"DRUG_INTERACTION"}, set()),
    ("two_nsaids_different_salts", [], ["Brufen 400", "Voveran 50"], "RED", {"DRUG_INTERACTION"}, {"DUPLICATE_SALT"}),
    ("meftal_plus_diclofenac", [], ["Meftal Spas", "Voveran 50"], "RED", {"DRUG_INTERACTION"}, set()),
    ("zerodol_sp_plus_dolo", [], ["Zerodol SP", "Dolo 650"], "RED", {"DUPLICATE_SALT"}, set()),
    ("nsaid_plus_warfarin", [], ["Voveran 50", "Warf 5"], "RED", {"DRUG_INTERACTION"}, set()),
    ("nsaid_plus_steroid", [], ["Brufen 400", "Wysolone 10"], "AMBER", {"DRUG_INTERACTION"}, {"DUPLICATE_SALT"}),
    ("two_arbs", [], ["Losar 50", "Olmezest 20"], "RED", {"DRUG_INTERACTION"}, set()),
    ("two_ace_inhibitors", [], ["Cardace 5", "Envas 5"], "RED", {"DRUG_INTERACTION"}, set()),
    ("ace_plus_arb", [], ["Cardace 5", "Telma 40"], "AMBER", {"DRUG_INTERACTION"}, set()),
    ("ace_plus_spironolactone", [], ["Cardace 5", "Aldactone 25"], "AMBER", {"DRUG_INTERACTION"}, set()),
    ("nsaid_plus_ace", [], ["Brufen 400", "Cardace 5"], "AMBER", {"DRUG_INTERACTION"}, set()),
    ("telma_h_plus_telma", [], ["Telma-H", "Telma 40"], "RED", {"DUPLICATE_SALT"}, set()),
    ("statin_in_combo_plus_statin", [], ["Rosuvas 10", "Ecosprin AV 75"], "RED", {"DRUG_INTERACTION"}, set()),
    ("two_ppis", ["Pan 40"], ["Pan 40", "Nexpro 40"], "AMBER", {"DRUG_INTERACTION"}, {"DUPLICATE_SALT"}),
    ("antibiotic_plus_warfarin", [], ["Azee 500", "Warf 5"], "AMBER", {"DRUG_INTERACTION"}, set()),
    ("wrong_strength_higher", ["Dolo 500"], ["Dolo 650"], "RED", {"DOSAGE_MISMATCH"}, set()),
    ("wrong_strength_lower", ["Dolo 650"], ["Dolo 500"], "AMBER", {"DOSAGE_MISMATCH"}, set()),
    ("brand_substitution_same_salt_same_strength", ["Dolo 650"], ["Pacimol 650"], "GREEN", {"MATCH"}, {"DOSAGE_MISMATCH"}),
    ("not_prescribed_extra_strip", ["Dolo 650"], ["Dolo 650", "Cetzine 10"], "AMBER", {"NOT_PRESCRIBED"}, set()),
    ("missing_strip", ["Dolo 650", "Telma 40"], ["Dolo 650"], "AMBER", {"MISSING_STRIP"}, set()),
    ("different_contents", ["Pan 40"], ["Pan-D"], "AMBER", {"SALT_MISMATCH"}, {"MATCH"}),
    ("unknown_brand", ["Dolo 650"], ["Dolo 650", "Zzqx Forte"], "AMBER", {"UNRECOGNISED"}, set()),
    ("nonexistent_strength", ["Telma 60"], ["Telma 40"], "AMBER", {"UNRECOGNISED"}, {"MATCH"}),
    ("thyroid_in_mcg_matches", ["Thyronorm 25"], ["Thyronorm 25"], "GREEN", {"MATCH"}, set()),
    ("crocin_advance_resolves", ["Crocin Advance 500"], ["Crocin Advance 500"], "GREEN", {"MATCH"}, set()),
    ("empty", [], [], "AMBER", {"NO_INPUT"}, set()),
    ("no_prescription", [], ["Dolo 650"], "AMBER", {"NO_PRESCRIPTION"}, {"MATCH"}),
    ("no_strips", ["Dolo 650"], [], "AMBER", {"NO_STRIPS"}, {"MATCH"}),
]


@pytest.mark.parametrize("sid,rx,strips,status,must,must_not", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_scenario(sid, rx, strips, status, must, must_not):
    r = run(rx, strips)
    codes = {f.code for f in r.findings}
    assert r.status == status, (sid, r.status, sorted(codes))
    assert must <= codes, (sid, "missing", must - codes, sorted(codes))
    assert not (must_not & codes), (sid, "unexpected", must_not & codes)
    if status != "GREEN":
        assert "All clear" not in r.summary_en  # only a verified match may say "all clear"


def test_unidentified_fragments_raise_one_card_not_two():
    # the real camera photo of a torn Dolo strip also yields fragments like "SnhletsIP"
    r = analyze([P(name="Dolo 650")], [S(name="Dolo-650", strength_mg=650), S(name="SnhletsIP")], TODAY)
    codes = [f.code for f in r.findings]
    assert codes.count("UNRECOGNISED") == 1
    assert [f.title for f in r.findings if f.code == "EXPIRY_MISSING"] == ["Expiry not read: Dolo 650"]
    assert r.status == "AMBER"  # never green while something could not be read


def test_expired_and_unreadable_dates_in_context():
    r = analyze([P(name="Dolo 650")], [S(name="Dolo 650", expiry="10/2026")], TODAY)
    assert "EXPIRED_BATCH" in {f.code for f in r.findings} and r.status == "RED"
    r = analyze([P(name="Dolo 650")], [S(name="Dolo 650", expiry="11/2026")], TODAY)  # valid through the end of November
    assert r.status == "GREEN"
    r = analyze([P(name="Dolo 650")], [S(name="Dolo 650", expiry="Mar 31 2026")], TODAY)
    assert "EXPIRY_UNREADABLE" in {f.code for f in r.findings}
