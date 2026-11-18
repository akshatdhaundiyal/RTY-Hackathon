# MediGuard — 3-Minute Demo Script & Talk Track

> **Context:** 3-minute pitch & live demonstration for judges at Buildathon ("Make Wednesdays Great Again").  
> **Target Audience:** Technical judges assessing **Working Product (1/3)**, **Problem Insight (1/3)**, and **Depth of Execution (1/3)**.  
> **Pre-demo warm-up:** The server loads RapidOCR and the local `gemma4:e2b` model by itself at startup (the page shows "Getting the on-device reader ready…" until that finishes, then the note disappears). Start the server and open the page a couple of minutes before presenting, and do one live upload as a rehearsal. A warm upload takes about 10-20 seconds; a cold one can take 1-2 minutes.

---

## 1. Quick Setup & Pre-Demo Checklist

- [ ] Ollama is running and `gemma4:e2b` is installed (`ollama list`).
- [ ] MediGuard server running on port `8000`:
  ```bash
  uv run uvicorn app:app --host 127.0.0.1 --port 8000
  ```
- [ ] Browser open to `http://127.0.0.1:8000` (full screen, zoom 110% for projection readability). The "getting ready" note is gone.
- [ ] Sound enabled on demo laptop. Press both read-aloud buttons once to confirm English and Hindi voices work (if the device has no Hindi voice, the Hindi button is disabled and the Hindi text is still shown on every card).
- [ ] Fixture files easily accessible in file picker (`fixtures/rx_sample.png` and `fixtures/strips_mismatch.png`).
- [ ] **Rehearsal upload done** (see warm-up note above).

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

**Speaker Action:** Stand next to screen showing MediGuard homepage (`http://127.0.0.1:8000`). Do not click buttons yet.

**Spoken Script:**
> "Many older people in India take several medicines a day, and the same medicine is sold under many brand names. Doctors prescribe by brand name, often in a hurry, and the pharmacy may hand over a different brand.
> 
> A patient is prescribed *Calpol 650*. At home they already have *Dolo 650* and some *Crocin*. Those are all paracetamol. Take two of them and you risk an overdose and liver damage, and nothing on the packet warns you. Add tiny foil print, expired strips in the bedside drawer, and interactions like *Brufen* (an NSAID) with *Ecosprin* (aspirin) causing bleeding, and keeping track becomes very hard for an elderly patient or their caregiver.
> 
> We built **MediGuard**: an offline-capable, bilingual (English and Hindi) medicine checker for elderly patients and their caregivers."

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
> 2. Green cards confirm that every strip matches the prescription (same active salt and strength), and no expiry problem was found (all dates run into 2027/2028).
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
> "Now the real pipeline. These are demo images: a typed prescription and a photo-style sheet of 5 medicine strips. Real phone photos work too, as long as the text is legible. Messy handwriting is the hard case, and when the text can't be read the app says so instead of guessing.
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
Highlight the key flags (there are also green cards for the matching strips):

1. **`DANGER — DUPLICATE SALT`**: Point to Dolo 650 & Crocin 500 card.
   > *"Look at this: Dolo 650 and Crocin 500 were both in the strip photo. MediGuard resolves both brand names to their underlying generic active ingredient—paracetamol—and immediately flags a dangerous double-dose overdose risk."*
2. **`DANGER — DOSAGE MISMATCH`**: Point to Dolo 650 card.
   > *"The doctor wrote Dolo 500 mg, but the chemist handed the patient Dolo 650 mg. MediGuard catches the higher-than-prescribed strength."*
3. **`DANGER — DRUG INTERACTION`**: Point to Brufen + Ecosprin card.
   > *"The patient had an unprescribed Brufen strip lying on the table. Taking Brufen (an NSAID) alongside prescribed Ecosprin (aspirin) creates a severe bleeding interaction. MediGuard flags it in bright red."*
4. **`DANGER — EXPIRED BATCH`**: Point to the Crocin 500 card.
   > *"And the Crocin strip expired in May 2026. MediGuard reads the printed expiry and flags it."*
5. **`CAUTION — NOT PRESCRIBED`**: Brufen and Crocin are flagged as not on the prescription.

**Spoken Script:**
> "Notice also our **Grounding Verification Layer**: MediGuard compares the raw OCR tokens with the LLM's output. If a medicine appears on the foil but the LLM missed it, or if the LLM hallucinated a medicine not seen in the OCR text, MediGuard flags an `UNGROUNDED_ENTRY` or `UNEXTRACTED_MEDICINE` AMBER warning.
> 
> Our safety core adheres to one strict rule: **When unsure, never guess, and never say all clear.**"

---

### [2:40 – 3:00] Summary & Close

**Speaker Action:** Click **`🔊 हिन्दी में सुनें`** on the red warning. Listen to: *"सावधान। समस्या मिली..."* then click **`Stop`**.

**Spoken Script:**
> "MediGuard works offline by default: the images are read on this laptop and never leave it. It reads warnings aloud in Hindi and English for elderly users, and it pairs AI text extraction with deterministic clinical rules that you can test line by line.
> 
> Thank you! We are happy to take your questions."

---

## 3. 30-Second Fallback Plan (If Live Upload Stalls)

If the laptop is under heavy load, Ollama cold-start takes longer than 20 seconds, or an image upload is interrupted:

1. **Do not panic or stall.**
2. Immediately say:  
   *"The on-device reader is still loading, so let me show the same check using our preset demo scenario. The rule engine and the result screen are identical."*
3. Click the top button: **`Scenario 2: Hidden Duplicate Salt + Interaction Trap`**.
4. The exact output renders instantly: Red banner, duplicate paracetamol detection, Brufen + Ecosprin interaction, and bilingual warning cards.
5. Continue the pitch seamlessly from Section [2:10].

---

## 4. 5 Likely Judge Questions & Crisp Technical Answers

### Q1: Why not let a multimodal LLM like GPT-4o or Gemini evaluate safety directly in the prompt?
> **Answer:** *"LLMs are probabilistic and prone to hallucination, sycophancy, and non-determinism. In healthcare, a 1% failure rate is catastrophic. If an LLM misses an interaction or invents a dosage, there is no audit trail. In MediGuard, the model has only one job: text extraction into strict JSON schemas. All clinical decisions—salt resolution, dosage checks, contraindications, and expiry dates—are 100% deterministic, reproducible, and verifiable in Python unit tests."*

### Q2: Indian doctor handwriting is notoriously unreadable. How does MediGuard cope with messy scripts and typos?
> **Answer:** *"Honestly, messy handwriting is the hard case: RapidOCR handles printed text well, but badly written text may not be read. We tested tilted, blurred, noisy and low-contrast photos, and the worst case, a heavy perspective skew, produced amber 'cannot identify' warnings instead of an all-clear. For typos in printed names, our brand resolver strips units and noise words ('tab', 'cap') and uses a similarity-ratio match against our Indian brand list. If a name can't be matched confidently, or a strength doesn't exist for that brand (like 'Telma 80'), it returns an amber `UNRECOGNISED` warning. It never guesses."*

### Q3: Why prioritize an offline local architecture over a cloud API?
> **Answer:** *"Two reasons: First, privacy—medical prescriptions and health records are sensitive personal data that patients and elderly users should not have to upload to third-party cloud servers. Second, accessibility in Tier-2/3 Indian cities and rural clinics where high-bandwidth internet is intermittent. MediGuard runs RapidOCR on the CPU and a compact local model (Ollama `gemma4:e2b`). Offline is the default. If a `GEMINI_API_KEY` is set, it uses Gemini instead and the images are sent to Google, and the page says which mode ran. If Gemini fails, it falls back to the on-device reader and tells the user."*

### Q4: How does MediGuard prevent prompt injection or hallucinated drugs from photo backgrounds?
> **Answer:** *"We implemented a dedicated Grounding Verification layer (`grounding_findings` in `safety_engine.py`). After extraction, the system cross-checks every extracted drug name against the raw OCR character tokens. If an entity was extracted that has no character footprint in the raw image, it flags `UNGROUNDED_ENTRY`. Conversely, if known pharmaceutical brand names appear in the OCR tokens but were missed by the extractor, it triggers `UNEXTRACTED_MEDICINE` in AMBER. Furthermore, system prompts explicitly instruct the model that OCR text is untrusted data."*

### Q5: What happens when a patient uploads a medicine that isn't in your database or has a torn expiry date?
> **Answer:** *"MediGuard never defaults to a false sense of security. If a drug is not in `drugs_db.json`, it returns `AMBER: UNRECOGNISED` with advice to consult a pharmacist. If the strip has no readable date or ambiguous dates, it returns `AMBER: EXPIRY_MISSING` or `AMBER: EXPIRY_UNREADABLE`. MediGuard will NEVER issue a GREEN 'All Clear' banner unless every single strip is positively verified against a prescription line."*
