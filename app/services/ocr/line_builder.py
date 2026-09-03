"""Text line reconstruction — ``app/services/ocr/line_builder.py`` (Phase 6).

OCR returns independent blocks, not the semantic lines a human reads. This
module groups blocks that sit on the same visual baseline into ordered
*lines*, so a manufacturer name split across blocks ("Manufactured / by /
ABC Foods") is recovered as one line.

Geometry-only grouping (deterministic):
    1. Sort blocks top-to-bottom by vertical center.
    2. Group blocks whose vertical centers fall within a band tolerance.
    3. Within each band, sort left-to-right and join normalized text.

A ``TextLine`` keeps a reference to its member blocks so provenance is never
lost.
"""

import math

from dataclasses import dataclass, field


@dataclass
class TextLine:
    """One reconstructed semantic line."""

    text: str
    index: int
    blocks: list = field(default_factory=list)
    y: int = 0

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "text": self.text,
            "y": self.y,
        }


def _band_tolerance(image_height: int) -> int:
    """Vertical-center band tolerance (px) scales with image size."""
    return max(12, int(image_height * 0.018))


def build_lines(blocks: list, image_height: int = 0) -> list[TextLine]:
    """Group normalized/engine blocks into ordered semantic lines.

    ``blocks`` may be NormalizedBlock, OCRBlock, or dicts exposing ``text``
    (or ``normalized_text``), ``bbox`` [x,y,w,h], and ``confidence``.

    Returns a list of TextLine ordered top-to-bottom, left-to-right.
    """
    records = []
    for b in blocks:
        text = _block_text(b)
        bbox = _block_bbox(b)
        if not text or not bbox:
            continue
        x, y, w, h = (int(v) for v in bbox)
        records.append(
            {
                "text": text,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "yc": y + h // 2,
                "conf": float(getattr(b, "confidence", b.get("confidence", 0.0) if isinstance(b, dict) else 0.0)),
                "block": b,
            }
        )

    tol = _band_tolerance(image_height)
    records.sort(key=lambda r: (r["yc"], r["x"]))

    lines: list[TextLine] = []
    for r in records:
        placed = False
        for line in lines:
            if abs(r["yc"] - _line_yof(line)) <= tol:
                line["blocks"].append(r)
                placed = True
                break
        if not placed:
            lines.append({"y": r["yc"], "blocks": [r]})

    result: list[TextLine] = []
    for i, line in enumerate(lines):
        members = sorted(line["blocks"], key=lambda r: r["x"])
        text = " ".join(m["text"] for m in members)
        result.append(
            TextLine(
                text=text,
                index=i,
                blocks=[m["block"] for m in members],
                y=line["y"],
            )
        )
    return result


def _line_yof(line: dict) -> float:
    return sum(r["yc"] for r in line["blocks"]) / len(line["blocks"])


def _block_text(b) -> str:
    if isinstance(b, dict):
        return (b.get("normalized_text") or b.get("text") or "").strip()
    return (getattr(b, "normalized_text", None) or getattr(b, "text", "") or "").strip()


def _block_bbox(b) -> list:
    if isinstance(b, dict):
        return b.get("bbox") or []
    return getattr(b, "bbox", None) or []


def join_lines(lines: list[TextLine]) -> str:
    """Join reconstructed lines into a normalized raw text block."""
    return "\n".join(line.text for line in lines)


def sort_lines_by_top(lines: list[TextLine]) -> list[TextLine]:
    """Return lines ordered top-to-bottom (stable)."""
    return sorted(lines, key=lambda ln: ln.y)


def _has_tol_approx(a: float, b: float) -> bool:
    return math.isclose(a, b, abs_tol=1.0)