"""OCR normalization — ``app/services/ocr/normalizer.py`` (Phase 5).

Because OCR engines are imperfect, every raw block needs a normalized form
that is still traceable to its source. This module turns each raw OCR reading
into a ``NormalizedBlock`` that keeps the verbatim ``raw_text`` alongside a
cleaned ``normalized_text``.

Normalization here is deliberately conservative (regex, non-destructive):
    - collapse internal runs of whitespace
    - drop stray tokens (noise) but never alter the meaning of genuine text
    - keep letters/digits/punctuation; remove likely OCR noise tokens

It never fabricates data. If nothing can be cleaned, ``normalized_text``
equals ``raw_text``.
"""

import re

# Noise tokens: OCR artifacts we strip. A token qualifies if it is all
# punctuation/symbols, or is a known garbage fragment (e.g. a lone underscore
# run, a bare ellipsis, bracketed OCR confidence remnants).
_NOISE_TOKEN = re.compile(r"^[\W_]+$")
_BRACKET_NOISE = re.compile(r"[\[{\(][^\]\)}\]]{0,12}[\]}\)]")


class NormalizedBlock:
    """A raw OCR block plus its normalized text and non-blank line."""

    __slots__ = ("raw_text", "normalized_text", "text", "confidence", "bbox")

    def __init__(self, raw_text: str, confidence: float, bbox: list[int]):
        self.raw_text = (raw_text or "").strip()
        self.normalized_text = normalize(raw_text)
        # ``text`` is the canonical display form (== normalized_text).
        self.text = self.normalized_text
        self.confidence = float(confidence)
        self.bbox = list(bbox)

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence": round(self.confidence, 4),
            "bbox": [int(v) for v in self.bbox],
        }


def normalize(raw: str) -> str:
    """Return a whitespace-normalized, noise-stripped version of ``raw``.

    Empty input -> empty string. Never returns None.
    """
    if not raw:
        return ""
    text = " ".join(raw.split())
    text = _BRACKET_NOISE.sub(" ", text)
    # Drop tokens made only of punctuation/symbols (e.g. "---", "!!!").
    tokens = [t for t in text.split() if not _NOISE_TOKEN.match(t)]
    return " ".join(tokens).strip()


def normalize_blocks(blocks: list) -> list[NormalizedBlock]:
    """Wrap engine blocks (or dicts) into NormalizedBlock list."""
    out = []
    for b in blocks:
        if hasattr(b, "raw_text"):
            out.append(NormalizedBlock(b.raw_text, b.confidence, b.bbox))
        else:
            out.append(
                NormalizedBlock(
                    b.get("text") or b.get("raw_text") or "",
                    b.get("confidence", 0.0),
                    b.get("bbox", [0, 0, 0, 0]),
                )
            )
    return out