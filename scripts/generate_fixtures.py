"""Generate fixture images for OCR testing.

Creates deterministic synthetic images containing printed text similar to
what a packaged-commodity label shows (MRP, net quantity, manufacturer,
dates, contact info). These are used ONLY to verify the pipeline runs and
to measure OCR success on OUR OWN dataset — not to claim general accuracy.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _font(size: int):
    """Find a usable TrueType font on this machine."""
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_card(text_lines: list[str], filename: str, size=(900, 1200)):
    """Draw a simple white label card with centered black text lines."""
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    font = _font(48)
    y = 120
    for line in text_lines:
        draw.text((80, y), line, fill="black", font=font)
        y += 90
    img.save(FIXTURE_DIR / filename)


def generate_all():
    """Generate the standard fixture set. Idempotent."""
    _draw_card(
        [
            "Premium Tea",
            "Net Wt. 500 g",
            "MRP Rs. 450",
            "Mfd. by ABC Foods Pvt Ltd",
            "Plot 12, Industrial Area, Delhi",
            "Made in India",
            "Batch No: BN-2601",
            "Packed: 08/2026",
            "Best Before: 24 months",
            "Customer Care: 1800-123-456",
        ],
        "valid_tea.jpg",
    )
    _draw_card(
        [
            "Salt",
            "Net Wt. 1 kg",
            "MRP Rs. 30",
            "Packed by Prachi Foods",
            "Pune, Maharashtra, India",
            "Batch No: SL-104",
            "Packed: 05/2026",
            "Best Before: 24 months",
            "Consumer Care: care@prachi.in",
        ],
        "valid_salt.jpg",
    )
    _draw_card(
        [
            "Biscuits",
            "Net Wt. 250 g",
            "MRP Rs. 40",
            "Mfd. by XYZ Snacks",
            "Plot 3, Whitefield, Bengaluru",
            "Made in India",
            "Batch No: BS-77",
            "Packed: 01/2026",
            "Best Before: 9 months",
            "Consumer Care: 1800-99-7777",
        ],
        "valid_biscuits.jpg",
    )
    _draw_card(
        [
            "Coffee",
            "Net Wt. 100 g",
            "MRP Rs. 200",
            "Instant Coffee",
        ],
        "missing_declarations.jpg",
    )
    print(f"Fixtures generated in {FIXTURE_DIR}")
    for f in sorted(FIXTURE_DIR.glob("*.jpg")):
        print(f"  {f.name}")


if __name__ == "__main__":
    generate_all()
