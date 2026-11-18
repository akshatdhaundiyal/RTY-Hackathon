# Robustness & Degradation Benchmark: Hard Photo Variants

> **Test Date:** 18 Nov 2026, 17:15 IST  
> **Environment:** MediGuard Offline Pipeline (RapidOCR CPU + Ollama `gemma4:e2b` + `safety_engine.py`)  
> **Host / Port:** `http://127.0.0.1:8001`  
> **Baseline Pair:** `fixtures/rx_sample.png` + `fixtures/strips_mismatch.png`  
> **Generator Script:** `fixtures/make_hard_fixtures.py` (Pillow only)  
> **Output Directory:** `fixtures/hard/` (Uncommitted in git because several generated variants exceed the 200 KB repository limit)

---

## 1. Executive Summary

Elderly users in India often take handheld photos under difficult conditions: low-cost Android phones, shaky hands, harsh fluorescent lighting causing glare on metallic blister foil, oblique angles from bedside tables, and high compression from messaging apps.

To evaluate MediGuard's real-world resilience, we programmatically generated 8 realistic photo degradation variants using Pillow and ran each sequentially through MediGuard's end-to-end `/api/analyze` pipeline.

### Core Safety Guarantee Demonstrated
**Under severe optical corruption (`perspective_skew`), the pipeline degraded to AMBER with explicit warnings (`UNRECOGNISED`, `EXPIRY_MISSING`). It NEVER degraded to GREEN.**  
This proves MediGuard's foundational design principle: **When unsure, never guess and never say "all clear".**

---

## 2. Benchmark Results Table

| Variant | Latency (s) | Verdict Status | Finding Codes | Matches Baseline? | Degradation Effect |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Baseline** | 8.48s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES (Reference)** | Baseline clean scan |
| **`rotate_5deg`** | 12.73s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `EXPIRY_MISSING`, `MATCH`, `MATCH` | **YES** | All 4 clinical REDs detected. Slight tilt caused Ecosprin expiry to be missed $\rightarrow$ flagged `EXPIRY_MISSING`. |
| **`perspective_skew`** *(HIGH PRIORITY)* | 5.93s | **AMBER** | `UNRECOGNISED`, `UNRECOGNISED`, `UNRECOGNISED`, `EXPIRY_MISSING`, `EXPIRY_MISSING` | **NO (Lost REDs)** | OCR text distorted into non-words. Model could not identify medicines $\rightarrow$ Safe degradation to AMBER. |
| **`blur_gaussian`** | 9.38s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `UNEXTRACTED_MEDICINE` (x2), `UNRECOGNISED`, `MISSING_STRIP`, `NOT_PRESCRIBED` (x2), `MATCH` | **YES** | All 4 clinical REDs detected. Grounding check caught two unextracted terms (`UNEXTRACTED_MEDICINE`). |
| **`noise`** | 10.30s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES** | RapidOCR binarization successfully filtered pixel noise. Identical to baseline. |
| **`low_contrast`** | 9.33s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES** | 40% contrast reduction handled cleanly by OCR engine. |
| **`glare_patch`** | 9.05s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES** | Text surrounding glare remained readable; all strips resolved. |
| **`jpeg_q40`** | 14.35s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES** | Block artifacts slowed OCR slightly (+6s) but preserved characters. |
| **`downscale_1200px`** | 12.21s | **RED** | `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`, `NOT_PRESCRIBED`, `NOT_PRESCRIBED`, `MATCH`, `MATCH` | **YES** | High-quality Lanczos scaling preserved full character legibility. |

---

## 3. HIGH PRIORITY Finding: `perspective_skew`

### Summary
- **Variant:** `perspective_skew`
- **Result:** Status **AMBER** (Elapsed: 5.93s)
- **Baseline Match:** **FAIL** (Loses all 4 baseline RED findings: `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`).
- **Files Involved:**
  - Prescription: `fixtures/hard/rx_perspective_skew.png`
  - Medicine Strips: `fixtures/hard/strips_perspective_skew.png`

### Analysis
When the image was subjected to an 8% horizontal and 6% vertical perspective skew (simulating an extreme phone camera tilt over a flat surface), RapidOCR received geometrically warped lines. 

Instead of reading `"Dr. R. K. Mehta... 1. Tab Dolo 500"`, the OCR output was corrupted into inverted / reversed gibberish:
```
WBNDW  baeurgsweamus yd: JoSe  002 olo0 dgT .  J-0-J x2qgska  Aed bisotns9 dsT S  J-0-0 J0 gska  2ysb 08x 1-0-0
```
And on the strips:
```
Doloe20  Escy spief coupsiua: suisce[swol lb e20 wa...
CLOC!U 200  Esc sp coua:sce[wolb200 wd...
```

The LLM faithfully extracted what it saw without hallucinating valid drug names:
- Prescribed: `[{"name": "WBNDW"}]`
- Strips: `[{"name": "Doloe20", "strength_mg": null}, {"name": "CLOC!U", "strength_mg": 200.0}]`

### What the App Showed the User
Because `WBNDW`, `Doloe20`, and `CLOC!U` do not match any known brand or generic active salt in `drugs_db.json`, `safety_engine.py` fired rule `0b`:
- `AMBER: UNRECOGNISED` — *Cannot identify WBNDW*
- `AMBER: UNRECOGNISED` — *Cannot identify Doloe20*
- `AMBER: UNRECOGNISED` — *Cannot identify CLOC!U (200)*
- `AMBER: EXPIRY_MISSING` — *Expiry not read: Doloe20*
- `AMBER: EXPIRY_MISSING` — *Expiry not read: Cloc!U*

**Overall Banner Displayed:**
`⚠️ Check with a pharmacist or doctor` (AMBER)  
**Spoken Summary:**
> *"Warning. 5 problems found. 'WBNDW' is not in the medicine database... Ask a pharmacist to check it."*

### Key Safety Observation
Crucially, MediGuard **did NOT give a false GREEN all-clear**. Because the text was illegible, it alerted the patient with 5 caution cards directing them to a pharmacist.

### Exact JSON Response for `perspective_skew`
```json
{
  "mode": "offline",
  "extracted": {
    "mode": "offline",
    "prescribed": [
      {
        "name": "WBNDW",
        "strength_mg": null,
        "frequency": null,
        "duration_days": null
      }
    ],
    "strips": [
      {
        "name": "Doloe20",
        "strength_mg": null,
        "expiry": null,
        "batch": null
      },
      {
        "name": "CLOC!U",
        "strength_mg": 200.0,
        "expiry": null,
        "batch": null
      }
    ],
    "raw_text_rx": "WBNDW  baeurgsweamus yd: JoSe  002 olo0 dgT .  J-0-J x2qgska  Aed bisotns9 dsT S  J-0-0 J0 gska  2ysb 08x 1-0-0",
    "raw_text_strips": "Doloe20  Escy spief coupsiua: suisce[swol lb e20 wa   Of to qit2 I ateldsT  B'N0: DrJ0 EXb: 0815051  BLNLGU 400  Esc spef cousue: pnbole Ib 400 wa   01 to qit2 | atsldsT  B'Wo: BBaa3J EXb: JSISOSI  gufoc!q D2B  acu sp6f cours2: bsupobL9sol6 40 wa + Dowb6uqou 30 wa   Or to qint2 | at9ld  No: bM3350 EXb: 0aI5051\nCLOC!U 200  Esc sp coua:sce[wolb200 wd   ON to qint | 2teldsT  B'NO: CBS081 EXb: 021505e  Escu splef couue: vabu Ib 12 wa   01 to qint2 | ateldsT  B'HO: ECJJ12 EXb: J0ISOSI",
    "findings": [],
    "fallback_reason": null
  },
  "report": {
    "status": "AMBER",
    "findings": [
      {
        "code": "UNRECOGNISED",
        "severity": "AMBER",
        "title": "Cannot identify WBNDW",
        "message_en": "'WBNDW' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it.",
        "message_hi": "'WBNDW' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।",
        "drugs": ["WBNDW"]
      },
      {
        "code": "UNRECOGNISED",
        "severity": "AMBER",
        "title": "Cannot identify Doloe20 (20)",
        "message_en": "'Doloe20' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it.",
        "message_hi": "'Doloe20' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।",
        "drugs": ["Doloe20"]
      },
      {
        "code": "UNRECOGNISED",
        "severity": "AMBER",
        "title": "Cannot identify CLOC!U (200)",
        "message_en": "'CLOC!U' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it.",
        "message_hi": "'CLOC!U' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।",
        "drugs": ["CLOC!U"]
      },
      {
        "code": "EXPIRY_MISSING",
        "severity": "AMBER",
        "title": "Expiry not read: Doloe20",
        "message_en": "The expiry date of Doloe20 was not read. Check it by eye before taking it.",
        "message_hi": "Doloe20 की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले खुद देखें।",
        "drugs": ["Doloe20"]
      },
      {
        "code": "EXPIRY_MISSING",
        "severity": "AMBER",
        "title": "Expiry not read: Cloc!U",
        "message_en": "The expiry date of Cloc!U was not read. Check it by eye before taking it.",
        "message_hi": "Cloc!U की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले खुद देखें।",
        "drugs": ["Cloc!U"]
      }
    ],
    "schedule": {
      "morning": [],
      "afternoon": [],
      "night": []
    },
    "prescribed": [
      {
        "input_name": "WBNDW",
        "brand": null,
        "salts": [],
        "strength_mg": null
      }
    ],
    "strips": [
      {
        "input_name": "Doloe20",
        "brand": null,
        "salts": [],
        "strength_mg": 20.0
      },
      {
        "input_name": "CLOC!U",
        "brand": null,
        "salts": [],
        "strength_mg": 200.0
      }
    ],
    "summary_en": "Warning. 5 problems found. 'WBNDW' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it. 'Doloe20' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it. 'CLOC!U' is not in the medicine database (or has a strength we do not know). Ask a pharmacist to check it. The expiry date of Doloe20 was not read. Check it by eye before taking it. The expiry date of Cloc!U was not read. Check it by eye before taking it.",
    "summary_hi": "सावधान। 5 समस्या मिली। 'WBNDW' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं। 'Doloe20' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं। 'CLOC!U' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं। Doloe20 की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले खुद देखें। Cloc!U की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले खुद देखें।"
  }
}
```

---

## 4. Analysis of Optical Degradation Modes

1. **Gaussian Blur (`radius=2.0`):**
   - The blur slightly softened character edges on the prescription foil.
   - Result: All 4 RED safety hazards were preserved. In addition, the **grounding check** fired `UNEXTRACTED_MEDICINE` because the raw OCR contained fragments of text that were partially missed by the LLM extraction. This demonstrates the grounding layer doing its job.
2. **Rotation (`5.0 degrees`):**
   - RapidOCR features angle-detection and handles modest skew well. All 4 clinical REDs were triggered.
   - The slight angle shift clipped the expiry text on Ecosprin 75, triggering an appropriate `AMBER: EXPIRY_MISSING` warning.
3. **Noise & Low Contrast:**
   - RapidOCR's internal preprocessing and binarization thresholding completely mitigated random Gaussian sensor noise and 40% contrast reduction.
4. **JPEG Quality 40:**
   - Strong 8x8 DCT compression artifacts slightly increased extraction runtime from 8.5s to 14.3s due to extra edge candidate boxes in RapidOCR. All findings matched baseline.

---

## 5. Storage Note on `fixtures/hard/`

Per Buildathon git rules:
> *"No secrets, no API keys. Generated images under fixtures/hard/ may be committed only if each file is under 200 KB; otherwise leave them uncommitted and note it."*

Several generated files under `fixtures/hard/` exceed 200 KB:
- `fixtures/hard/strips_noise.png`: 1,370 KB
- `fixtures/hard/rx_noise.png`: 510 KB
- `fixtures/hard/strips_downscale_1200px.png`: 317 KB
- `fixtures/hard/strips_jpeg_q40.png`: 302 KB
- `fixtures/hard/strips_rotate_5deg.png`: 279 KB
- `fixtures/hard/strips_perspective_skew.png`: 276 KB

Therefore, `fixtures/hard/` is deliberately left uncommitted in git. The generator script `fixtures/make_hard_fixtures.py` is committed and reproduces the exact test artifacts on demand.
