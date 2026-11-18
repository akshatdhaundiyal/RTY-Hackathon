"""MediGuard FastAPI app. Run: uvicorn app:app --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from safety_engine import PhysicalStrip, PrescribedDrug, analyze

ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"
app = FastAPI(title="MediGuard")


def scenarios() -> dict:
    return json.loads((FIXTURES / "scenarios.json").read_text(encoding="utf-8"))


class VerifyRequest(BaseModel):
    prescribed: list[PrescribedDrug]
    strips: list[PhysicalStrip]


@app.get("/api/scenarios")
def list_scenarios():
    return [{"id": k, "title": v["title"], "rx_image": f"/fixtures/{v['rx_image']}",
             "strips_image": f"/fixtures/{v['strips_image']}"} for k, v in scenarios().items()]


@app.post("/api/analyze")
def analyze_images(scenario: Optional[str] = Form(None), rx: Optional[UploadFile] = File(None),
                   strips: Optional[UploadFile] = File(None)):
    """Preset scenario (instant, no OCR/LLM) or uploaded images (OCR/Gemini -> rules)."""
    if scenario:
        sc = scenarios().get(scenario)
        if not sc:
            raise HTTPException(404, "Unknown scenario")
        rx_list = [PrescribedDrug(**p) for p in sc["prescribed"]]
        st_list = [PhysicalStrip(**s) for s in sc["strips"]]
        return {"mode": "scenario", "extracted": {"prescribed": sc["prescribed"], "strips": sc["strips"]},
                "report": analyze(rx_list, st_list)}
    if not rx or not strips:
        raise HTTPException(400, "Provide both a prescription image and a medicine strips image.")
    from vision_extractor import extract  # lazy: keeps startup fast / OCR model loads on first use
    try:
        res = extract(rx.file.read(), strips.file.read())
    except Exception as e:  # never guess on failure
        raise HTTPException(503, f"Could not read the images ({type(e).__name__}: {e}). "
                                 "Is Ollama running? Try a demo scenario instead.")
    return {"mode": res.mode, "extracted": res.model_dump(),
            "report": analyze(res.prescribed, res.strips)}


@app.post("/api/verify")
def verify(req: VerifyRequest):
    return {"report": analyze(req.prescribed, req.strips)}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/fixtures", StaticFiles(directory=FIXTURES), name="fixtures")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
