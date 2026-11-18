"""Guard rails for the committed real product photos (no OCR here: that needs Ollama)."""
from pathlib import Path

from PIL import Image

REAL = Path(__file__).resolve().parent.parent / "fixtures" / "real"
IMAGES = sorted(p for p in REAL.iterdir() if p.suffix.lower() in {".jpeg", ".jpg", ".png"})


def test_photos_exist_are_readable_and_small():
    assert IMAGES, "fixtures/real should contain the product photos"
    for p in IMAGES:
        assert p.stat().st_size < 400 * 1024, f"{p.name} is too large for the repo"
        with Image.open(p) as im:
            im.verify()


def test_every_photo_is_listed_in_the_attribution_notice():
    notice = (REAL / "ATTRIBUTION.md").read_text(encoding="utf-8")
    for p in IMAGES:
        assert f"`{p.name}`" in notice, f"{p.name} is missing from ATTRIBUTION.md"
    assert "were not recorded" in notice  # the notice must not pretend to know a licence


def test_file_names_do_not_contradict_the_content_notes():
    names = {p.name for p in IMAGES}
    assert "dolo500.jpeg" not in names  # that strip is Dolo-650
