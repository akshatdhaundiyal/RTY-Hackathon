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


def test_llm_ocr_glitches():
    assert resolve("TabPantocidDSR").brand == "pantocid dsr"
    assert resolve("Tab Dolo", 500).brand == "dolo 500"
    assert parse_frequency("1-0-1x") == ["morning", "night"]


def test_never_all_clear_on_empty_or_one_sided():
    for r, code in [(analyze([], [], TODAY), "NO_INPUT"),
                    (analyze([], [S(name="Dolo 650", expiry="08/2027")], TODAY), "NO_PRESCRIPTION"),
                    (analyze([P(name="Dolo 650")], [], TODAY), "NO_STRIPS")]:
        assert r.status == "AMBER" and code in codes(r)
        assert "All clear" not in r.summary_en


def test_wrong_strength_is_not_silently_remapped():
    for name, mg in [("Telma", 80), ("Pan", 20), ("Dolo", 1000), ("Losar", 25), ("Warf", 2)]:
        assert resolve(name, mg).salts == [], name
    r = analyze([P(name="Telma", strength_mg=80)], [S(name="Telma", strength_mg=40, expiry="03/2028")], TODAY)
    assert r.status != "GREEN" and "UNRECOGNISED" in codes(r)
    assert resolve("Dolo 650 SR").salts == []  # different formulation is not Dolo 650


def test_combo_names_keep_all_salts():
    assert resolve("Pan D").salts == ["pantoprazole", "domperidone"]
    r = analyze([], [S(name="Zerodol P"), S(name="Dolo 650")], TODAY)
    assert "DUPLICATE_SALT" in codes(r)


def test_expiry_ignores_mfg_and_batch_dates():
    assert parse_expiry("B.No 12/26 EXP 03/25") == date(2025, 3, 31)
    assert parse_expiry("MFG 03/2024 EXP 02/2027") == date(2027, 2, 28)
    assert parse_expiry("Mfg Jan-23 Exp Jan-26") == date(2026, 1, 31)
    assert parse_expiry("B.No:DL4410EXP:08/2027") == date(2027, 8, 31)
    assert parse_expiry("03-15-2027") is None  # ambiguous, not 2015
    assert parse_expiry("Mar 31 2026") is None
    assert parse_expiry("MFG 01/2024 12/2025") == date(2025, 12, 31)
    r = analyze([], [S(name="Dolo 650", expiry="B.No 12/26 EXP 03/25")], TODAY)
    assert "EXPIRED_BATCH" in codes(r)


def test_attached_units_and_generics():
    assert resolve("Warfarin 5mg").salts == ["warfarin"]
    r = analyze([], [S(name="Warfarin 5mg", expiry="03/2028"), S(name="Brufen 400", expiry="03/2028")], TODAY)
    inter = [f for f in r.findings if f.code == "DRUG_INTERACTION"]
    assert inter and inter[0].severity == "RED"


def test_partial_salt_overlap_is_not_a_match():
    for rx_name, strip_name in [("Pan 40", "Pan-D"), ("Combiflam", "Brufen 400")]:
        r = analyze([P(name=rx_name)], [S(name=strip_name, expiry="03/2028")], TODAY)
        assert "SALT_MISMATCH" in codes(r) and "MATCH" not in codes(r) and r.status != "GREEN"


def test_one_strip_serves_one_prescription_line():
    r = analyze([P(name="Warf 5"), P(name="Warf 5")], [S(name="Warf 5", expiry="03/2028")], TODAY)
    assert "DUPLICATE_PRESCRIPTION" in codes(r)


def test_grounding_flags_dropped_and_invented_entries():
    from safety_engine import grounding_findings
    text = "Dolo 650  Crocin 500\nParacetamol IP 650 mg  Paracetamol IP 500 mg"
    dropped = grounding_findings(text, [resolve("Dolo", 650)], "strips")
    assert any(f.code == "UNEXTRACTED_MEDICINE" and "Crocin" in f.title for f in dropped)
    invented = grounding_findings(text, [resolve("Dolo", 650), resolve("Warfarin", 5)], "strips")
    assert any(f.code == "UNGROUNDED_ENTRY" for f in invented)
    assert not grounding_findings(text, [resolve("Dolo", 650), resolve("Crocin", 500)], "strips")


def test_trap_scenario_pairs_same_brand_and_keeps_all_findings():
    import json
    sc = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))
    expect = {"safe": ({"MATCH"}, "GREEN"),
              "trap": ({"DUPLICATE_SALT", "DOSAGE_MISMATCH", "DRUG_INTERACTION", "EXPIRED_BATCH", "NOT_PRESCRIBED"}, "RED")}
    for key, (want, status) in expect.items():
        v = sc[key]
        r = analyze([P(**p) for p in v["prescribed"]], [S(**s) for s in v["strips"]], TODAY)
        assert r.status == status and want <= codes(r), (key, codes(r))


def test_frequency():
    assert parse_frequency("1-0-1") == ["morning", "night"]
    assert parse_frequency("TDS") == ["morning", "afternoon", "night"]
    assert parse_frequency("at night") == ["night"]


def test_additional_interactions_and_blank_names():
    r1 = analyze([], [S(name="Clopilet 75"), S(name="Omez 20")], TODAY)
    assert any(f.code == "DRUG_INTERACTION" and f.severity == "AMBER" for f in r1.findings)
    r2 = analyze([], [S(name="Metrogyl 400"), S(name="Warf 5")], TODAY)
    assert any(f.code == "DRUG_INTERACTION" and f.severity == "RED" for f in r2.findings)
    r3 = analyze([], [S(name="   ")], TODAY)
    assert any(f.code == "UNRECOGNISED" and "unrecognised" in f.title.lower() for f in r3.findings)


def test_image_mime_detection():
    from vision_extractor import _image_mime
    assert _image_mime(b"\x89PNG\r\n\x1a\n...") == "image/png"
    assert _image_mime(b"\xff\xd8\xff\xe0...") == "image/jpeg"
    assert _image_mime(b"RIFF\x00\x00\x00\x00WEBP...") == "image/webp"
    assert _image_mime(b"unknown bytes") == "image/png"

