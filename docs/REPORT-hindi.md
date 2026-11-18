# Hindi Translation & Localization Audit: MediGuard

> **Audit Date:** 18 Nov 2026  
> **Auditor Role:** Bilingual Medical Proofreader & Senior AI Specialist  
> **Focus:** Verification of vernacular Hindi strings across `safety_engine.py`, `drugs_db.json`, `static/index.html`, and `vision_extractor.py`.  
> **Scope:** Report only (source files remain untouched per buildathon constraints).

---

## 1. Executive Summary & Localization Principles

In India, senior citizens (and their domestic or family caregivers) are the primary demographic relying on vernacular voice read-aloud and UI text for safety warnings. 

Our audit evaluated all Hindi strings against three key criteria:
1. **Clinical Correctness & Completeness:** Does the Hindi warning preserve every clinical nuance from the English warning (e.g. whether a dosage mismatch is an overdose or underdose; whether an interaction risks kidneys or blunts heart protection)?
2. **Elder Accessibility & Natural Tone:** Elderly North Indian Hindi speakers do not speak highly Sanskritized Hindi (e.g., *छवियों*), nor do they appreciate overly abrupt phrasing (e.g., *खुद देखें*). They respond best to respectful (*कृपया... खुद जांचें*), conversational Hindustani with familiar terms (*फ़ोटो*, *पर्चा*, *स्ट्रिप*).
3. **Grammatical Agreement in Dynamic Templates:** Ensuring plural agreement when counting issues (e.g., `1 समस्या मिली है` vs `6 समस्याएं मिली हैं`).

---

## 2. Comprehensive Proofreading Table

| Location (`file:line`) | Current Text | Suggested Text | Reason for Recommendation |
| :--- | :--- | :--- | :--- |
| **`safety_engine.py:314`** | `{side} के टेक्स्ट में '{term}' दिख रहा है पर उसे दवा के रूप में नहीं पढ़ा गया। खुद देखें।` | `{side_hi} में '{term}' लिखा दिख रहा है, पर इसे दवा के रूप में नहीं पढ़ा गया। कृपया खुद देखकर पुष्टि करें।` | 1. `{side}` is untranslated English (`prescription`/`medicine strips`). Map to *पर्चे* / *दवा की स्ट्रिप*.<br>2. *"खुद देखें"* sounds curt and dismissive to elderly users; *"कृपया खुद देखकर पुष्टि करें"* is respectful and clinically appropriate. |
| **`safety_engine.py:323`** | `'{r.input_name}' निकाली गई पर {side} के टेक्स्ट में नहीं मिली। खुद देखें।` | `'{r.input_name}' पहचानी गई, लेकिन यह {side_hi} में नहीं मिली। कृपया खुद जांच लें।` | *"निकाली गई"* implies physical extraction (like pulling an object); for text OCR, *"पहचानी गई"* or *"पढ़ी गई"* is accurate. |
| **`safety_engine.py:354`** | `छवियों से कोई दवा नहीं पढ़ी जा सकी। साफ़ फोटो लें या खुद जांचें।` | `फ़ोटो में से कोई भी दवा नहीं पढ़ी जा सकी। कृपया साफ़ फ़ोटो लें या पर्चा खुद जांचें।` | *"छवियों"* is hyper-formal/Sanskritized; elderly users and everyday caregivers in India consistently say *"फ़ोटो"*. |
| **`safety_engine.py:358`** | `कोई दवा की स्ट्रिप नहीं पढ़ी जा सकी, इसलिए पर्चे से जांच नहीं हो सकी।` | `दवा की कोई स्ट्रिप नहीं पढ़ी जा सकी, इसलिए पर्चे से मिलान नहीं हो सका।` | 1. Word order correction (*दवा की कोई स्ट्रिप* instead of *कोई दवा की स्ट्रिप*).<br>2. *"मिलान"* (matching/verification) is more precise than *"जांच"* (inspection). |
| **`safety_engine.py:362`** | `कोई पर्चा नहीं पढ़ा जा सका, इसलिए स्ट्रिप की जांच पर्चे से नहीं हो सकी।` | `पर्चे की फ़ोटो पढ़ी नहीं जा सकी, इसलिए दवाओं का मिलान नहीं हो सका।` | Cleaner sentence flow and natural cadence. |
| **`safety_engine.py:372`** | `'{name_disp}' हमारे डेटाबेस में नहीं है। कृपया फार्मासिस्ट से जांच करवाएं।` | `'{name_disp}' हमारी दवा सूची (डेटाबेस) में नहीं है। कृपया फार्मासिस्ट या डॉक्टर से जांच करवाएं।` | Elderly patients may not know what a "database" is; adding *"दवा सूची"* aids comprehension. |
| **`safety_engine.py:385`** | `{' और '.join(names)} दोनों में {salt} है। दोनों लेने से ओवरडोज़ हो सकता है। केवल एक ही लें।` | `{' और '.join(names)} दोनों में {salt} है। दोनों दवाएं एक साथ लेने से ओवरडोज़ (हानिकारक अधिक मात्रा) हो सकता है। केवल एक ही दवा लें।` | Clarifies the clinical hazard of overdose for patients who may not know the English term *"overdose"*. |
| **`safety_engine.py:399`** | `पर्चे में {' और '.join(names)} दोनों में {salt} है। डॉक्टर से पूछें कि क्या यह सही है।` | `पर्चे में {' और '.join(names)} दोनों में एक ही घटक ({salt}) है। डॉक्टर से पुष्टि करें कि क्या दोनों दवाएं लेनी हैं।` | Clearer action item for the patient when consulting their doctor. |
| **`safety_engine.py:426`** *(HIGH IMPACT)* | `डॉक्टर ने {pr.strength_mg:g} mg लिखी है पर स्ट्रिप पर {sr.strength_mg:g} mg है। फार्मासिस्ट से पूछें।` | `डॉक्टर ने {pr.strength_mg:g} mg लिखी है पर स्ट्रिप पर {sr.strength_mg:g} mg है ({'पर्चे से अधिक मात्रा' if over else 'पर्चे से कम मात्रा'})। फार्मासिस्ट से पूछें।` | **Clinical discrepancy:** The English text tells the user whether the dose is *higher* or *lower* than prescribed (`over`), which determines whether it is a RED toxicity risk or an AMBER under-treatment risk. The Hindi string currently omits this crucial detail. |
| **`safety_engine.py:432`** | `{_label(sr)} पर्चे से मेल खाती है।` | `{_label(sr)} पर्चे से पूरी तरह मेल खाती है।` | Current string is accurate; *"पूरी तरह"* adds reassuring confirmation on a GREEN card. |
| **`safety_engine.py:437`** | `{_label(sr)} की मात्रा पर्चे से मिलाई नहीं जा सकी। खुद देखें।` | `{_label(sr)} की पावर/स्ट्रेंथ (mg) पर्चे से मिलाई नहीं जा सकी। कृपया खुद देखकर जांच लें।` | In Hindi colloquial medical usage, *"पावर"* or *"स्ट्रेंथ (mg)"* is widely understood by elders, whereas *"मात्रा"* can be confused with tablet count (quantity). |
| **`safety_engine.py:449`** | `{_label(pr)} लिखी गई है पर {_label(sr)} में अलग दवाएं ({', '.join(sr.salts)}) हैं। फार्मासिस्ट से पूछें।` | `{_label(pr)} लिखी गई है, पर स्ट्रिप {_label(sr)} में अलग घटक ({', '.join(sr.salts)}) हैं। यह वही दवा नहीं है; फार्मासिस्ट से पूछें।` | Reinforces that the blister strip is not a direct substitute. |
| **`safety_engine.py:455`** | `{_label(pr)} लिखी गई है लेकिन उसकी स्ट्रिप नहीं मिली।` | `पर्चे में {_label(pr)} लिखी है, लेकिन फ़ोटो में इसकी कोई स्ट्रिप नहीं मिली।` | Clarifies that the strip was missing from the uploaded table photo. |
| **`safety_engine.py:461`** | `{_label(sr)} पर्चे में नहीं है। डॉक्टर से पूछे बिना न लें।` | `{_label(sr)} पर्चे में नहीं लिखी है। डॉक्टर से पूछे बिना इसे बिल्कुल न लें।` | Stronger cautionary emphasis (*बिल्कुल न लें*) against unprescribed pills. |
| **`safety_engine.py:492`** | `{_label(r)} की एक्सपायरी तारीख नहीं पढ़ी गई। लेने से पहले खुद देखें।` | `{_label(r)} की एक्सपायरी तारीख फ़ोटो में नहीं पढ़ी जा सकी। दवा लेने से पहले स्ट्रिप पर खुद ज़रूर जांचें।` | More natural phrasing emphasizing the need to inspect the physical blister foil. |
| **`safety_engine.py:499`** | `{_label(r)} की एक्सपायरी तारीख '{s.expiry}' पढ़ी नहीं जा सकी। खुद देखें।` | `{_label(r)} पर लिखी एक्सपायरी तारीख '{s.expiry}' स्पष्ट नहीं है। कृपया स्ट्रिप पर खुद जांच लें।` | Explains why the date couldn't be confirmed (unclear/smudged printing). |
| **`safety_engine.py:504`** | `{_label(r)} की एक्सपायरी {d:%d/%m/%Y} को खत्म हो चुकी है। इसे न खाएं।` | `{_label(r)} की एक्सपायरी तारीख ({d:%d/%m/%Y}) बीत चुकी है। यह दवा खराब हो चुकी है, इसे बिल्कुल न खाएं।` | *"एक्सपायरी खत्म हो चुकी है"* is tautological / colloquial. *"तारीख बीत चुकी है... दवा खराब हो चुकी है"* is natural and clear. |
| **`safety_engine.py:516`** | `{_label(pr)} के लिए लिखा समय ('{p.frequency}') रोज़ के कार्यक्रम में नहीं बदला जा सका। डॉक्टर या फार्मासिस्ट से पूछें कि कब लेनी है।` | `{_label(pr)} के लेने का समय ('{p.frequency}') रोज़ के शेड्यूल में नहीं समझ आया। डॉक्टर या फार्मासिस्ट से पूछें कि यह दवा कब लेनी है।` | *"रोज़ के कार्यक्रम"* sounds like an event agenda or daily program. *"रोज़ के शेड्यूल"* or *"दैनिक समय"* is standard Indian medical parlance. |
| **`safety_engine.py:523`** | `कोई भी दवा पर्चे से सत्यापित नहीं हो सकी। खुद जांचें।` | `पर्चे से किसी भी दवा का मिलान नहीं हो सका। कृपया स्वयं जांच करें।` | *"सत्यापित"* is bureaucratic Hindi; *"मिलान"* is natural. |
| **`safety_engine.py:532`** | `सब ठीक है। आपकी दवाएं पर्चे से मेल खाती हैं।` | `सब ठीक है। आपकी सभी दवाएं पर्चे से मेल खाती हैं।` | Excellent, concise baseline string. |
| **`safety_engine.py:535`** *(GRAMMATICAL DEFECT)* | `f"सावधान। {len(bad)} समस्या मिली। "` | `f"सावधान। {len(bad)} समस्या{'एं' if len(bad) > 1 else ''} मिली{'ं' if len(bad) > 1 else ''}। "` $\rightarrow$ *(e.g. 6 समस्याएं मिलीं)* | **Grammar defect:** When `len(bad) > 1` (e.g. 6 problems in Scenario 2), saying *"6 समस्या मिली"* is grammatically singular and sounds awkward. Correct Hindi plural agreement is *"6 समस्याएं मिलीं"*. |
| **`drugs_db.json:67`** | `दर्द की दवा (NSAID) और खून पतला करने वाली दवा साथ लेने से गंभीर अंदरूनी रक्तस्राव हो सकता है।` | *(Current is good)* | Accurate, clear, and perfectly balances medical explanation with layman understanding. |
| **`drugs_db.json:70`** | `दर्द की दवा के साथ एस्पिरिन या क्लोपिडोग्रेल लेने से रक्तस्राव का खतरा बढ़ता है।` | `दर्द की दवा के साथ एस्पिरिन या क्लोपिडोग्रेल लेने से रक्तस्राव का खतरा बढ़ता है और दिल की सुरक्षा का असर कम हो सकता है।` | English source includes *"and can blunt aspirin's heart protection"*; adding this makes the Hindi warning complete. |
| **`drugs_db.json:73`** | `एस्पिरिन या क्लोपिडोग्रेल के साथ वारफेरिन लेने से रक्तस्राव का खतरा बहुत बढ़ जाता है।` | *(Current is good)* | Clear and accurate. |
| **`drugs_db.json:76`** | `दो अलग दर्द निवारक (NSAID) साथ लेने से पेट और गुर्दे को नुकसान हो सकता है।` | *(Current is good)* | Clear and accurate. |
| **`drugs_db.json:79`** | `मेट्रोनिडाज़ोल वारफेरिन का असर बहुत बढ़ा देता है, रक्तस्राव हो सकता है।` | `मेट्रोनिडाज़ोल वारफेरिन का असर बहुत बढ़ा देता है, जिससे गंभीर रक्तस्राव (ब्लीडिंग) हो सकता है।` | Better flow and connects cause to effect. |
| **`drugs_db.json:82`** | `सिप्रोफ्लॉक्सासिन वारफेरिन का असर बढ़ा सकता है। डॉक्टर से जांच के बारे में पूछें।` | *(Current is good)* | Accurate. |
| **`drugs_db.json:85`** | `एज़िथ्रोमाइसिन वारफेरिन का असर बढ़ा सकता है। डॉक्टर से पूछें।` | *(Current is good)* | Accurate. |
| **`drugs_db.json:88`** | `दर्द की दवा बीपी की दवा का असर कम कर सकती है और गुर्दों पर असर डाल सकती है।` | *(Current is good)* | *"बीपी की दवा"* and *"गुर्दों पर असर"* are well-suited for elders. |
| **`drugs_db.json:91`** | `दर्द की दवा पानी निकालने वाली दवा का असर कम कर सकती है।` | `दर्द की दवा पानी निकालने वाली दवा (diuretic) का असर कम कर सकती है और गुर्दों पर दबाव डाल सकती है।` | English source includes *"and strain the kidneys"*; the Hindi text currently omits the kidney warning. |
| **`drugs_db.json:94`** | `टेल्मिसर्टन/लोसार्टन के साथ स्पिरोनोलैक्टोन से पोटैशियम खतरनाक स्तर तक बढ़ सकता है।` | *(Current is good)* | Clear and accurate. |
| **`drugs_db.json:97`** | `एक ही प्रकार की दो बीपी की दवाएं (ARB) साथ लेने से गुर्दे को नुकसान और पोटैशियम बढ़ सकता है।` | *(Current is good)* | Clear and accurate. |
| **`drugs_db.json:100`** | `कोलेस्ट्रॉल की दो दवाएं (स्टैटिन) साथ लेने से मांसपेशियों को गंभीर नुकसान का खतरा बढ़ता है।` | *(Current is good)* | Clear and accurate. |
| **`drugs_db.json:103`** | `एसिडिटी की एक ही प्रकार की दो दवाएं (PPI) साथ लेने से कोई फायदा नहीं, साइड इफेक्ट बढ़ सकते हैं।` | *(Current is good)* | Clear and natural. |
| **`drugs_db.json:106`** | `एलर्जी की दो दवाएं साथ लेने से बहुत नींद आ सकती है।` | `एलर्जी की दो दवाएं साथ लेने से बहुत अधिक सुस्ती और नींद आ सकती है।` | *"बहुत अधिक सुस्ती और नींद"* clarifies drowsiness. |
| **`drugs_db.json:109`** | `ओमेप्राज़ोल क्लोपिडोग्रेल का असर कम कर सकता है। डॉक्टर से पूछें।` | `ओमेप्राज़ोल क्लोपिडोग्रेल का असर कम कर सकता है (आमतौर पर पैंटोप्राज़ोल बेहतर विकल्प है)। डॉक्टर से पूछें।` | English includes *"Pantoprazole is usually preferred"*; beneficial clinical alternative. |
| **`vision_extractor.py:161`** | `{label} में बहुत ज़्यादा टेक्स्ट है, इसलिए केवल पहला हिस्सा पढ़ा गया। बाकी खुद देखें।` | `{label} में बहुत ज़्यादा लिखावट है, इसलिए केवल शुरुआती हिस्सा पढ़ा गया है। बाकी खुद ध्यान से जांच लें।` | Polite and clear phrasing for OCR text truncation warning. |
| **`static/index.html:186`** | `<button id="hi" class="sec" lang="hi">🔊 हिन्दी में सुनें</button>` | *(Current is good)* | Short, accessible, and immediately recognizable for Hindi speakers. |

---

## 3. Top Recommendations for Future Refactoring

When the code freeze lifts or the team opens post-buildathon polish:

1. **Fix Pluralization in Summary Header (`safety_engine.py:535`):**
   Change:
   ```python
   # Current:
   hi = f"सावधान। {len(bad)} समस्या मिली। " + " ".join(f.message_hi for f in bad)
   
   # Recommended:
   s_term = "समस्या" if len(bad) == 1 else "समस्याएं"
   v_term = "मिली है" if len(bad) == 1 else "मिली हैं"
   hi = f"सावधान। {len(bad)} {s_term} {v_term}। " + " ".join(f.message_hi for f in bad)
   ```
2. **Translate Dosage Mismatch Severity (`safety_engine.py:426`):**
   Include `(पर्चे से अधिक)` or `(पर्चे से कम)` so the Hindi voice output mirrors the English clinical guidance on whether the patient is taking an overdose or underdose.
3. **Harmonize Missing Kidney Warnings in `drugs_db.json`:**
   Add *गुर्दों पर दबाव डाल सकती है* to interaction rule 8 (`nsaid + diuretic`) to align with the English clinical text.
