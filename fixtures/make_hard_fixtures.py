"""Generate harder photo variants using Pillow only. Run: python fixtures/make_hard_fixtures.py"""
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
SRC_RX = ROOT / "rx_sample.png"
SRC_STRIPS = ROOT / "strips_mismatch.png"
OUT_DIR = ROOT / "hard"


def ensure_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def variant_rotation(img: Image.Image, degrees: float = 5.0) -> Image.Image:
    """Rotate image by 3-8 degrees with white background fill."""
    return img.rotate(degrees, resample=Image.BICUBIC, expand=True, fillcolor=(250, 248, 240))


def variant_perspective(img: Image.Image) -> Image.Image:
    """Perspective skew simulating an angle photo from a mobile phone."""
    w, h = img.size
    # Map input rectangle to a trapezoid
    dx = int(w * 0.08)
    dy = int(h * 0.06)
    coeffs = (
        0, 0,
        w, 0,
        w - dx, h - dy,
        dx, h
    )
    # PIL transform QUAD takes target bounding box (0, 0, w, h) mapped from quad in source
    return img.transform((w, h), Image.QUAD, coeffs, resample=Image.BICUBIC, fillcolor=(240, 240, 240))


def variant_blur(img: Image.Image, radius: float = 2.0) -> Image.Image:
    """Simulate camera out-of-focus motion or lens blur."""
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def variant_noise(img: Image.Image, strength: float = 25.0) -> Image.Image:
    """Add sensor noise (salt & pepper / random fluctuations)."""
    random.seed(42)
    im = img.convert("RGB")
    pixels = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            delta = int(random.gauss(0, strength))
            pixels[x, y] = (
                max(0, min(255, r + delta)),
                max(0, min(255, g + delta)),
                max(0, min(255, b + delta)),
            )
    return im


def variant_low_contrast(img: Image.Image, factor: float = 0.4) -> Image.Image:
    """Simulate washed-out lighting or poor exposure."""
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(factor)


def variant_glare(img: Image.Image) -> Image.Image:
    """Simulate flash glare or overhead tube light reflection on blister foil."""
    im = img.convert("RGBA")
    overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = im.size
    # Draw an elliptical bright white glare hotspot with feathering
    bbox = (int(w * 0.25), int(h * 0.25), int(w * 0.70), int(h * 0.65))
    draw.ellipse(bbox, fill=(255, 255, 255, 185))
    combined = Image.alpha_composite(im, overlay)
    return combined.convert("RGB")


def variant_jpeg_q40(img: Image.Image) -> Image.Image:
    """Simulate severe JPEG compression artifacts from WhatsApp / low-end phone."""
    import io
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=40)
    buf.seek(0)
    return Image.open(buf).copy()


def variant_downscale_1200px(img: Image.Image) -> Image.Image:
    """Scale width to 1200px (standard phone capture downscale budget)."""
    w, h = img.size
    target_w = 1200
    target_h = int(h * (target_w / w))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


VARIANTS = [
    ("rotate_5deg", lambda im: variant_rotation(im, 5.0)),
    ("perspective_skew", variant_perspective),
    ("blur_gaussian", lambda im: variant_blur(im, 2.0)),
    ("noise", variant_noise),
    ("low_contrast", lambda im: variant_low_contrast(im, 0.4)),
    ("glare_patch", variant_glare),
    ("jpeg_q40", variant_jpeg_q40),
    ("downscale_1200px", variant_downscale_1200px),
]


def make_all():
    ensure_dir()
    rx = Image.open(SRC_RX)
    st = Image.open(SRC_STRIPS)

    created = []
    for name, fn in VARIANTS:
        rx_out = OUT_DIR / f"rx_{name}.png"
        st_out = OUT_DIR / f"strips_{name}.png"

        im_rx = fn(rx)
        im_st = fn(st)

        im_rx.save(rx_out)
        im_st.save(st_out)

        size_rx = rx_out.stat().st_size
        size_st = st_out.stat().st_size
        created.append((name, rx_out, size_rx, st_out, size_st))
        print(f"Generated {name:20s} -> rx: {size_rx/1024:.1f} KB, strips: {size_st/1024:.1f} KB")

    return created


if __name__ == "__main__":
    make_all()
