"""Image -> structured entities. Two modes:

* online : Gemini Vision (if GEMINI_API_KEY is set)
* offline: RapidOCR (CPU/ONNX, no VRAM) -> local Ollama gemma4:e2b, temperature 0, JSON-schema constrained

The LLM only *extracts and normalises text into schemas*. It never judges safety;
that is safety_engine.py's job.
"""
from __future__ import annotations

import io
import json
import os
from typing import Optional

import httpx
import numpy as np
from PIL import Image
from pydantic import BaseModel

from safety_engine import PhysicalStrip, PrescribedDrug

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class RxExtraction(BaseModel):
    drugs: list[PrescribedDrug]


class StripExtraction(BaseModel):
    strips: list[PhysicalStrip]


class ExtractionResult(BaseModel):
    mode: str  # "gemini" | "offline"
    prescribed: list[PrescribedDrug]
    strips: list[PhysicalStrip]
    raw_text_rx: Optional[str] = None
    raw_text_strips: Optional[str] = None


RX_PROMPT = (
    "You read Indian medical prescriptions. Extract every prescribed medicine as JSON "
    '{"drugs":[{"name","strength_mg","frequency","duration_days"}]}. '
    "name = brand or generic name exactly as written WITHOUT the strength. strength_mg = number in mg or null. "
    "frequency = dosing pattern as written (e.g. 1-0-1, BD, TDS, HS) or null. Use null when unsure. "
    "Do NOT invent medicines. Output JSON only."
)
STRIP_PROMPT = (
    "You read printed medicine blister strips / boxes. Extract every distinct strip as JSON "
    '{"strips":[{"name","strength_mg","expiry","batch"}]}. '
    "name = brand name as printed WITHOUT the strength. strength_mg = number in mg or null. "
    "expiry = exactly as printed (e.g. 03/2027 or Mar-27) or null. Use null when unsure. "
    "Do NOT invent strips. Output JSON only."
)

_ocr = None


def _ocr_engine():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def ocr_text(image_bytes: bytes) -> str:
    """Local OCR, grouped into reading-order lines."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result, _ = _ocr_engine()(np.array(img))
    if not result:
        return ""
    items = []
    for box, text, _score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((sum(ys) / 4, min(xs), max(ys) - min(ys), text))
    items.sort()
    lines: list[list[tuple]] = []
    for it in items:
        if lines and abs(it[0] - lines[-1][0][0]) < max(10, it[2] * 0.6):
            lines[-1].append(it)
        else:
            lines.append([it])
    return "\n".join("  ".join(t for *_, t in sorted(ln, key=lambda x: x[1])) for ln in lines)


def _ollama_json(prompt: str, text: str, schema: dict) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0},
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"OCR TEXT:\n{text}"},
        ],
    }
    with httpx.Client(timeout=300) as c:
        r = c.post(f"{OLLAMA_URL}/api/chat", json=payload)
        if r.status_code == 400 and "think" in r.text.lower():
            payload.pop("think")
            r = c.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def extract_offline(rx_img: bytes, strips_img: bytes) -> ExtractionResult:
    rx_text, st_text = ocr_text(rx_img), ocr_text(strips_img)
    rx = RxExtraction(**_ollama_json(RX_PROMPT, rx_text, RxExtraction.model_json_schema()))
    st = StripExtraction(**_ollama_json(STRIP_PROMPT, st_text, StripExtraction.model_json_schema()))
    return ExtractionResult(mode="offline", prescribed=rx.drugs, strips=st.strips,
                            raw_text_rx=rx_text, raw_text_strips=st_text)


def extract_gemini(rx_img: bytes, strips_img: bytes) -> ExtractionResult:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def call(prompt: str, img: bytes, model_cls):
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt],
            config=types.GenerateContentConfig(
                temperature=0, response_mime_type="application/json", response_schema=model_cls),
        )
        return model_cls.model_validate_json(resp.text)

    rx = call(RX_PROMPT, rx_img, RxExtraction)
    st = call(STRIP_PROMPT, strips_img, StripExtraction)
    return ExtractionResult(mode="gemini", prescribed=rx.drugs, strips=st.strips)


def extract(rx_img: bytes, strips_img: bytes) -> ExtractionResult:
    """Gemini when a key is configured; transparently fall back to offline on any failure."""
    if os.getenv("GEMINI_API_KEY"):
        try:
            return extract_gemini(rx_img, strips_img)
        except Exception:
            pass
    return extract_offline(rx_img, strips_img)
