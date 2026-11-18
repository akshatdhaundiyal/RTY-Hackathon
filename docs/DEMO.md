# MediGuard — 3-Minute Demo Script & Talk Track

> **Context:** 3-minute pitch & live demonstration for judges at Buildathon ("Make Wednesdays Great Again").  
> **Target Audience:** Technical judges assessing **Working Product (1/3)**, **Problem Insight (1/3)**, and **Depth of Execution (1/3)**.  
> **Speaker Pre-Demo Warmup:** Run one real OCR/LLM query before the presentation so the local Ollama `gemma4:e2b` weights and RapidOCR models are preloaded in memory.

---

## 1. Quick Setup & Pre-Demo Checklist

- [ ] MediGuard server running on port `8001`:
  ```bash
  uv run uvicorn app:app --host 127.0.0.1 --port 8001
  ```
- [ ] Browser open to `http://127.0.0.1:8001` (full screen, zoom 110% for projection readability).
- [ ] Sound enabled on demo laptop (test Web Speech API audio for English and Hindi text-to-speech).
- [ ] Fixture files easily accessible in file picker (`fixtures/rx_sample.png` and `fixtures/strips_mismatch.png`).
- [ ] **Warmup performed:** Send a test request via curl or UI 5 minutes prior to avoid cold-start delays.

---

## 2. Talk Track & Demo Flow (180 Seconds Total)

```
0:00 — 0:35  | Problem Insight: The Polypharmacy Trap in India
0:35 — 1:15  | Working Product: Scenario 1 (Safe Baseline)
1:15 — 2:10  | Depth of Execution & Live Upload: Scenario 2 & Live Pipeline
2:10 — 2:40  | Clinical Rule Engine & Safety Architecture Deep Dive
2:40 — 3:00  | Summary & Judge Hand-off
```

---

### [0:00 – 0:35] Problem Insight (Judging Criterion: 1/3)

**Speaker Action:** Stand next to screen showing MediGuard homepage (`http://127.0.0.1:8001`). Do not click buttons yet.

**Spoken Script:**
> "In India, over 140 million senior citizens take 4 to 8 medicines every single day. But here is the silent danger: in India, doctors prescribe by brand name or hasty handwriting, and patients buy whatever generic brand the local pharmacy stocks.
> 
> A patient gets prescribed *Calpol 650*. At home, they already have *Dolo 650* from yesterday and *Crocin* from last week. They don't know that all three are identical: Paracetamol. They take two, and within days they risk acute acetaminophen toxicity and liver damage. Add in tiny foil print, expired strips in bedside drawers, and lethal drug interactions—like taking *Brufen* (an NSAID) with *Ecosprin* (aspirin) causing gastric bleeding—and managing medicines becomes Russian roulette for an elderly patient.
> 
> We built **MediGuard**: an offline-capable, bilingual medication verifier designed specifically for Indian households and caregivers."

---

### [0:35 – 1:15] Working Product — Baseline Scenario (Judging Criterion: 1/3)

**Speaker Action:**
1. Point to top header: *"💊 MediGuard"*.
2. Click the button: **`Scenario 1: Safe Match`**.
3. Point out how the UI instantly updates with the seeded prescription and strips.

**Spoken Script:**
> "Let's start with what a correct medication check looks like. With one click on **Scenario 1**, MediGuard checks a prescription of Dolo 650, Telma 40, and Pantocid DSR against matching blister strips.
> 
> Notice what happens:
> 1. The top banner turns solid **GREEN**: *'All clear — medicines match the prescription'*.
> 2. The finding cards confirm that every strip matches the active salt, strength, and valid expiry date (all valid into 2027/2028).
> 3. Below that, it automatically parses complex Indian prescription timing (like *1-0-1* or *1-0-0*) into an accessible **Daily Schedule**: Morning pill badges, Afternoon, and Night badges.
> 4. And for an elder who cannot read small text, they click one button..."

**Speaker Action:**
Click **`🔊 Read aloud (English)`** or **`🔊 हिन्दी में सुनें`**. Let it speak the first sentence ("All clear. Your medicines match the prescription" / "सब ठीक है..."), then click **`Stop`**.

---

### [1:15 – 2:10] Depth of Execution & Live Upload (Judging Criterion: 1/3)

**Speaker Action:**
1. Scroll back to upload zones.
2. Under **1. Prescription**, click **`Choose file`** $\rightarrow$ select `fixtures/rx_sample.png`.
3. Under **2. Medicine strips**, click **`Choose file`** $\rightarrow$ select `fixtures/strips_mismatch.png`.
4. Click **`Verify my medicines`** button. The loading spinner shows: *"Reading the images… the first run can take a minute or two."*

**Spoken Script:**
> "Now let's test a realistic, chaotic Indian scenario. Here is a real prescription photo with multiple handwritten medicines, and here is a photo of 5 medicine strips on a bedside table.
> 
> Watch what our pipeline is doing under the hood right now:
> First, **RapidOCR** extracts text blocks in reading order on the local CPU without needing massive GPU memory.
> Second, a local Ollama model—**gemma4:e2b**—extracts structured entities conforming to strict Pydantic JSON schemas.
> 
> But here is our fundamental architectural principle:
> **The LLM is NEVER allowed to judge medical safety.**
> LLMs hallucinate, LLMs suffer from sycophancy, and LLMs cannot be trusted with lethal dosages.
> 
> The LLM only parses text into structured JSON. That JSON is then fed into our **deterministic clinical rule engine** backed by `drugs_db.json`."

*(If running live upload finishes in 5-15s after warmup, let results show. If running on a slow laptop without GPU, immediately pivot using the 30-Second Fallback Plan below.)*

---

### [2:10 – 2:40] Scenario 2: The Trap Revealed

**Speaker Action:**
Point to the big red banner: **`⛔ Do NOT take these medicines until checked`**.
Highlight the four distinct critical flags:

1. **`DANGER — DUPLICATE SALT`**: Point to Dolo 650 & Crocin 500 card.
   > *"Look at this: Dolo 650 and Crocin 500 were both in the strip photo. MediGuard resolves both brand names to their underlying generic active ingredient—paracetamol—and immediately flags a dangerous double-dose overdose risk."*
2. **`DANGER — DOSAGE MISMATCH`**: Point to Dolo 650 card.
   > *"The doctor wrote Dolo 500 mg, but the chemist handed the patient Dolo 650 mg. MediGuard catches the higher-than-prescribed strength."*
3. **`DANGER — DRUG INTERACTION`**: Point to Brufen + Ecosprin card.
   > *"The patient had an unprescribed Brufen strip lying on the table. Taking Brufen (an NSAID) alongside prescribed Ecosprin (aspirin) creates a severe bleeding interaction. MediGuard flags it in bright red."*
4. **`CAUTION — NOT PRESCRIBED`**: Brufen is flagged as unprescribed.

**Spoken Script:**
> "Notice also our **Grounding Verification Layer**: MediGuard compares the raw OCR tokens with the LLM's output. If a medicine appears on the foil but the LLM missed it, or if the LLM hallucinated a medicine not seen in the OCR text, MediGuard flags an `UNGROUNDED_ENTRY` or `UNEXTRACTED_MEDICINE` AMBER warning.
> 
> Our safety core adheres to one strict rule: **When unsure, never guess, and never say all clear.**"

---

### [2:40 – 3:00] Summary & Close

**Speaker Action:** Click **`🔊 हिन्दी में सुनें`** on the red warning. Listen to: *"सावधान। समस्या मिली..."* then click **`Stop`**.

**Spoken Script:**
> "MediGuard requires zero internet connection to protect lives. It works fully offline on everyday laptops or clinic PCs, supports vernacular Hindi read-aloud for senior citizens, and combines modern vision AI extraction with the uncompromised determinism of clinical rules.
> 
> Thank you! We are happy to take your questions."

---

## 3. 30-Second Fallback Plan (If Live Upload Stalls)

If the laptop is under heavy load, Ollama cold-start takes longer than 20 seconds, or an image upload is interrupted:

1. **Do not panic or stall.**
2. Immediately say:  
   *"While the local OCR and 2-billion parameter vision model finish quantizing on this single laptop CPU, let me show you the exact deterministically parsed scenario via our seeded benchmark button."*
3. Click the top button: **`Scenario 2: Hidden Duplicate Salt + Interaction Trap`**.
4. The exact output renders instantly: Red banner, duplicate paracetamol detection, Brufen + Ecosprin interaction, and bilingual warning cards.
5. Continue the pitch seamlessly from Section [2:10].

---

## 4. 5 Likely Judge Questions & Crisp Technical Answers

### Q1: Why not let a multimodal LLM like GPT-4o or Gemini evaluate safety directly in the prompt?
> **Answer:** *"LLMs are probabilistic and prone to hallucination, sycophancy, and non-determinism. In healthcare, a 1% failure rate is catastrophic. If an LLM misses an interaction or invents a dosage, there is no audit trail. In MediGuard, the model has only one job: text extraction into strict JSON schemas. All clinical decisions—salt resolution, dosage checks, contraindications, and expiry dates—are 100% deterministic, reproducible, and verifiable in Python unit tests."*

### Q2: Indian doctor handwriting is notoriously unreadable. How does MediGuard cope with messy scripts and typos?
> **Answer:** *"We use a multi-stage defense. RapidOCR provides bounding-box reading order on device. Then, our brand resolver in `safety_engine.py` runs a normalized token matching algorithm: stripping dosage units and noise words ('tab', 'cap', 'ip'), matching brand stems, and using Levenshtein ratio matching against our verified Indian brand database. Crucially, if a brand name cannot be matched with high confidence, or if a strength doesn't match known formulations (like an impossible 'Telma 800'), it degrades gracefully to an `AMBER: UNRECOGNISED` alert. It never guesses."*

### Q3: Why prioritize an offline local architecture over a cloud API?
> **Answer:** *"Two reasons: First, privacy—medical prescriptions and health records are sensitive personal data that patients and elderly users should not have to upload to third-party cloud servers. Second, accessibility in Tier-2/3 Indian cities and rural clinics where high-bandwidth internet is intermittent. MediGuard runs on standard hardware using RapidOCR on CPU and a compact quantized local model (Ollama `gemma4:e2b`). If an online `GEMINI_API_KEY` is present, it can use it, but if cloud fails, it automatically falls back offline and explicitly informs the user."*

### Q4: How does MediGuard prevent prompt injection or hallucinated drugs from photo backgrounds?
> **Answer:** *"We implemented a dedicated Grounding Verification layer (`grounding_findings` in `safety_engine.py`). After extraction, the system cross-checks every extracted drug name against the raw OCR character tokens. If an entity was extracted that has no character footprint in the raw image, it flags `UNGROUNDED_ENTRY`. Conversely, if known pharmaceutical brand names appear in the OCR tokens but were missed by the extractor, it triggers `UNEXTRACTED_MEDICINE` in AMBER. Furthermore, system prompts explicitly instruct the model that OCR text is untrusted data."*

### Q5: What happens when a patient uploads a medicine that isn't in your database or has a torn expiry date?
> **Answer:** *"MediGuard never defaults to a false sense of security. If a drug is not in `drugs_db.json`, it returns `AMBER: UNRECOGNISED` with advice to consult a pharmacist. If the strip has no readable date or ambiguous dates, it returns `AMBER: EXPIRY_MISSING` or `AMBER: EXPIRY_UNREADABLE`. MediGuard will NEVER issue a GREEN 'All Clear' banner unless every single strip is positively verified against a prescription line."*
