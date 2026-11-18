"""Comprehensive coverage tests for deterministic clinical verification in safety_engine.py.

Covers:
- Every drug interaction rule in drugs_db.json using real brand names.
- Expiry date formats (MM/YYYY, MM/YY, MMM-YY, 'EXP 03/2027', etc.).
- Target finding codes: NOT_PRESCRIBED, MISSING_STRIP, SALT_MISMATCH, STRENGTH_UNVERIFIED, EXPIRY_MISSING.
"""
from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import safety_engine as se
from safety_engine import PhysicalStrip as S, PrescribedDrug as P, analyze, parse_expiry

TODAY = date(2026, 11, 18)


def get_finding_codes(report):
    return [f.code for f in report.findings]


def get_findings_by_code(report, code):
    return [f for f in report.findings if f.code == code]


# ============================================================================
# 1. TEST EVERY INTERACTION RULE IN drugs_db.json "interactions"
# ============================================================================

INTERACTION_TEST_CASES = [
    # (rule_index, description, brand_a, brand_b, expected_severity)
    (0, "nsaid + anticoagulant", "Brufen 400", "Warf 5", "RED"),
    (1, "nsaid + antiplatelet", "Brufen 400", "Ecosprin 75", "RED"),
    (2, "antiplatelet + anticoagulant", "Ecosprin 75", "Warf 5", "RED"),
    (3, "nsaid + nsaid", "Brufen 400", "Voveran 50", "RED"),
    (4, "metronidazole + warfarin", "Metrogyl 400", "Warf 5", "RED"),
    (5, "ciprofloxacin + warfarin", "Ciplox 500", "Warf 5", "AMBER"),
    (6, "azithromycin + warfarin", "Azithral 500", "Warf 5", "AMBER"),
    (7, "nsaid + arb", "Brufen 400", "Telma 40", "AMBER"),
    (8, "nsaid + diuretic", "Brufen 400", "Lasix 40", "AMBER"),
    (9, "arb + k_sparing", "Telma 40", "Aldactone 25", "AMBER"),
    (10, "arb + arb", "Telma 40", "Losar 50", "RED"),
    (11, "statin + statin", "Atorva 10", "Rosuvas 10", "RED"),
    (12, "ppi + ppi", "Pan 40", "Omez 20", "AMBER"),
    (13, "antihistamine + antihistamine", "Cetzine 10", "Allegra 120", "AMBER"),
    (14, "clopidogrel + omeprazole", "Clopilet 75", "Omez 20", "AMBER"),
]


@pytest.mark.parametrize("idx,desc,brand_a,brand_b,expected_sev", INTERACTION_TEST_CASES)
def test_all_15_interactions_fire_with_real_brands(idx, desc, brand_a, brand_b, expected_sev):
    rule = se.INTERACTIONS[idx]
    assert rule["severity"] == expected_sev, f"Rule {idx} severity mismatch in drugs_db.json"

    # Present both as physical strips
    report = analyze(
        prescribed=[],
        strips=[
            S(name=brand_a, expiry="12/2028"),
            S(name=brand_b, expiry="12/2028"),
        ],
        today=TODAY,
    )
    interactions = get_findings_by_code(report, "DRUG_INTERACTION")
    assert interactions, f"Interaction rule {idx} ({desc}) did not fire for {brand_a} + {brand_b}"

    # Verify that at least one interaction finding matches the expected severity
    matching = [f for f in interactions if f.severity == expected_sev]
    assert matching, f"Interaction rule {idx} fired but expected severity {expected_sev} not found"


def test_interaction_between_prescribed_and_strip():
    """Interaction triggers even when one drug is prescribed (no strip) and one is a strip."""
    report = analyze(
        prescribed=[P(name="Warf 5", frequency="1-0-0")],
        strips=[S(name="Brufen 400", expiry="12/2028")],
        today=TODAY,
    )
    interactions = get_findings_by_code(report, "DRUG_INTERACTION")
    assert interactions
    assert interactions[0].severity == "RED"


# ============================================================================
# 2. TEST EXPIRY DATE FORMATS
# ============================================================================

@pytest.mark.parametrize("raw_date,expected", [
    ("03/2027", date(2027, 3, 31)),
    ("05/26", date(2026, 5, 31)),
    ("Dec-27", date(2027, 12, 31)),
    ("dec-27", date(2027, 12, 31)),
    ("DEC-27", date(2027, 12, 31)),
    ("Mar-28", date(2028, 3, 31)),
    ("EXP 03/2027", date(2027, 3, 31)),
    ("EXP. 03/2027", date(2027, 3, 31)),
    ("EXP: 03/2027", date(2027, 3, 31)),
    ("exp 08/2027", date(2027, 8, 31)),
    ("3/2027", date(2027, 3, 31)),
    ("03/27", date(2027, 3, 31)),
    ("12/28", date(2028, 12, 31)),
    ("AUG/2027", date(2027, 8, 31)),
    ("B.No:DL4410 EXP:08/2027", date(2027, 8, 31)),
    ("MFG 01/2024 EXP 01/2027", date(2027, 1, 31)),
])
def test_parse_expiry_formats(raw_date, expected):
    parsed = parse_expiry(raw_date)
    assert parsed == expected, f"Failed parsing expiry '{raw_date}': got {parsed}, expected {expected}"


# ============================================================================
# 3. TEST TARGET FINDING CODES
# ============================================================================

def test_finding_not_prescribed():
    """Strip present on table that was never prescribed."""
    report = analyze(
        prescribed=[P(name="Dolo 650", frequency="1-0-1")],
        strips=[
            S(name="Dolo 650", expiry="08/2027"),
            S(name="Brufen 400", expiry="08/2027"),
        ],
        today=TODAY,
    )
    findings = get_findings_by_code(report, "NOT_PRESCRIBED")
    assert findings
    assert findings[0].severity == "AMBER"
    assert "Brufen 400" in findings[0].drugs


def test_finding_missing_strip():
    """Prescribed medicine has no corresponding strip on the table."""
    report = analyze(
        prescribed=[
            P(name="Dolo 650", frequency="1-0-1"),
            P(name="Telma 40", frequency="1-0-0"),
        ],
        strips=[S(name="Dolo 650", expiry="08/2027")],
        today=TODAY,
    )
    findings = get_findings_by_code(report, "MISSING_STRIP")
    assert findings
    assert findings[0].severity == "AMBER"
    assert "Telma 40" in findings[0].drugs


def test_finding_salt_mismatch():
    """Prescription calls for a combo drug, but strip only contains one salt."""
    report = analyze(
        prescribed=[P(name="Combiflam", frequency="1-0-1")],  # ibuprofen 400 + paracetamol 325
        strips=[S(name="Brufen 400", expiry="08/2027")],       # ibuprofen 400 only
        today=TODAY,
    )
    findings = get_findings_by_code(report, "SALT_MISMATCH")
    assert findings
    assert findings[0].severity == "AMBER"
    assert "Combiflam" in findings[0].drugs or "Brufen 400" in findings[0].drugs


def test_finding_strength_unverified():
    """Brand specified without strength where multiple strengths exist, so strength is unverified."""
    report = analyze(
        prescribed=[P(name="Dolo")],  # Dolo exists as 500 and 650, so strength is None
        strips=[S(name="Dolo", expiry="08/2027")],
        today=TODAY,
    )
    findings = get_findings_by_code(report, "STRENGTH_UNVERIFIED")
    assert findings
    assert findings[0].severity == "AMBER"


def test_finding_expiry_missing():
    """Strip has no expiry date printed or read."""
    report = analyze(
        prescribed=[P(name="Dolo 650", frequency="1-0-1")],
        strips=[S(name="Dolo 650", expiry=None)],
        today=TODAY,
    )
    findings = get_findings_by_code(report, "EXPIRY_MISSING")
    assert findings
    assert findings[0].severity == "AMBER"
    assert "Dolo 650" in findings[0].drugs


def test_finding_expiry_unreadable():
    """Strip has an unparseable or ambiguous expiry date string."""
    report = analyze(
        prescribed=[P(name="Dolo 650", frequency="1-0-1")],
        strips=[S(name="Dolo 650", expiry="invalid-date-999")],
        today=TODAY,
    )
    findings = get_findings_by_code(report, "EXPIRY_UNREADABLE")
    assert findings
    assert findings[0].severity == "AMBER"
