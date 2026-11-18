import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vision_extractor as vx
from safety_engine import PhysicalStrip, PrescribedDrug


def png(size=(40, 40), fmt="PNG"):
    b = io.BytesIO()
    Image.new("RGB", size, "white").save(b, fmt)
    return b.getvalue()


def test_prepare_image_accepts_png_and_jpeg_and_downsizes():
    assert vx.prepare_image(png()).startswith(b"\x89PNG")
    assert vx.prepare_image(png(fmt="JPEG")).startswith(b"\x89PNG")  # normalised
    big = Image.open(io.BytesIO(vx.prepare_image(png((5000, 100)))))
    assert max(big.size) <= vx.MAX_SIDE


@pytest.mark.parametrize("data,status", [(b"", 400), (b"not an image", 415), (b"x" * (vx.MAX_IMAGE_BYTES + 1), 413)])
def test_prepare_image_rejects_bad_uploads(data, status):
    with pytest.raises(vx.ImageError) as e:
        vx.prepare_image(data, "test image")
    assert e.value.status == status


def test_tiny_images_are_enlarged_but_normal_ones_are_not():
    tiny = Image.open(io.BytesIO(vx.prepare_image(png((244, 206)))))
    assert max(tiny.size) >= 900 and max(tiny.size) <= 244 * vx.MAX_UPSCALE
    normal = Image.open(io.BytesIO(vx.prepare_image(png((500, 400)))))
    assert normal.size == (500, 400)  # not enlarged: that made OCR repeat text on real strips


def test_repeated_strip_listings_merge_without_losing_distinct_strips():
    S = PhysicalStrip
    out = vx.merge_repeats([S(name="BRUFEN", strength_mg=400), S(name="Brufen", strength_mg=400, expiry="12/2027"),
                            S(name="BRUFEN", strength_mg=400), S(name="Combiflam"), S(name="Combiflam")])
    assert [(s.name, s.expiry) for s in out] == [("BRUFEN", "12/2027"), ("Combiflam", None)]
    # different batches are different strips; different strengths are different strips
    out = vx.merge_repeats([S(name="Dolo", strength_mg=650, batch="A1"), S(name="Dolo", strength_mg=650, batch="B2"),
                            S(name="Dolo", strength_mg=500)])
    assert len(out) == 3
    rx = vx.merge_repeats([PrescribedDrug(name="Dolo", strength_mg=650), PrescribedDrug(name="dolo", strength_mg=650)])
    assert len(rx) == 1


def test_llm_number_coercion():
    assert PrescribedDrug(name="Dolo", strength_mg="650mg", duration_days="5 days").strength_mg == 650
    assert PrescribedDrug(name="Dolo", strength_mg="650mg", duration_days="5.5").duration_days == 5
    assert PrescribedDrug(name="Dolo", strength_mg=0).strength_mg is None  # 0 means unknown
    assert PhysicalStrip(name="Dolo", strength_mg="").strength_mg is None
    assert PhysicalStrip(name="Dolo", strength_mg="unknown").strength_mg is None


def test_ollama_down_is_a_safe_typed_error(monkeypatch):
    monkeypatch.setattr(vx, "OLLAMA_URL", "http://127.0.0.1:9")  # nothing listens here
    with pytest.raises(vx.ExtractionError) as e:
        vx._ollama_extract("x", "text", vx.RxExtraction)
    assert "127.0.0.1" not in e.value.public and "Ollama" in e.value.public


def test_gemini_failure_falls_back_and_says_so(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(vx, "extract_gemini", lambda a, b: (_ for _ in ()).throw(RuntimeError("quota")))
    monkeypatch.setattr(vx, "extract_offline", lambda a, b: vx.ExtractionResult(mode="offline", prescribed=[], strips=[]))
    res = vx.extract(png(), png())
    assert res.mode == "offline" and "Gemini" in res.fallback_reason and "quota" not in res.fallback_reason


def test_second_concurrent_extraction_is_refused(monkeypatch):
    assert vx._gate.acquire(blocking=False)
    try:
        with pytest.raises(vx.BusyError):
            vx.extract(png(), png())
    finally:
        vx._gate.release()


def test_long_ocr_text_is_clipped_with_a_warning():
    findings = []
    out = vx._clip("a" * (vx.MAX_OCR_CHARS + 10), "prescription", findings)
    assert len(out) == vx.MAX_OCR_CHARS and findings[0].code == "OCR_TRUNCATED"


def test_warm_up_reports_ready_unavailable_and_never_raises(monkeypatch):
    monkeypatch.setattr(vx, "ocr_text", lambda b: "")
    monkeypatch.setattr(vx, "_ollama_extract", lambda *a, **k: None)
    vx.warm_up()
    assert vx.WARM["state"] == "ready" and vx.WARM["seconds"] is not None

    def down(*a, **k):
        raise vx.ExtractionError("Ollama is not running.")
    monkeypatch.setattr(vx, "_ollama_extract", down)
    vx.warm_up()
    assert vx.WARM["state"] == "unavailable" and "Ollama" in vx.WARM["detail"]

    monkeypatch.setattr(vx, "ocr_text", lambda b: (_ for _ in ()).throw(RuntimeError("boom")))
    vx.warm_up()  # must not raise
    assert vx.WARM["state"] == "unavailable" and "boom" not in vx.WARM["detail"]


def test_status_endpoint_and_startup_hook(monkeypatch):
    from fastapi.testclient import TestClient
    import app as appmod

    started = []
    monkeypatch.setattr(vx, "warm_up", lambda: started.append(1))
    monkeypatch.setenv("MEDIGUARD_WARMUP", "1")
    with TestClient(appmod.app) as c:  # entering the context runs the startup hook
        s = c.get("/api/status").json()
    assert set(s) >= {"state", "detail", "gemini_configured"}
    import time; time.sleep(0.2)
    assert started == [1]


def test_api_error_mapping_and_fixture_whitelist():
    from fastapi.testclient import TestClient
    import app as appmod

    c = TestClient(appmod.app)
    r = c.post("/api/analyze", files={"rx": ("a.png", b"not an image"), "strips": ("b.png", png())})
    assert r.status_code == 415 and "readable image" in r.json()["detail"]
    assert c.post("/api/analyze", data={"scenario": "nope"}).status_code == 404
    assert c.post("/api/analyze", data={"scenario": "safe"}).json()["report"]["status"] == "GREEN"
    assert c.get("/fixtures/rx_safe.png").status_code == 200
    assert c.get("/fixtures/make_fixtures.py").status_code == 404
    assert c.get("/fixtures/scenarios.json").status_code == 404
    assert c.get("/fixtures/..%2Fapp.py").status_code == 404
