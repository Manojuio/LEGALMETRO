"""Tests for OCR engine Phases 5/6/12: normalizer, line_builder, visualization."""

import numpy as np
import pytest

from app.services.ocr import normalizer
from app.services.ocr.line_builder import build_lines, join_lines, TextLine
from app.services.ocr.visualization import draw_ocr_boxes


# ---------- Phase 5: normalizer ----------

def test_normalize_collapses_whitespace():
    assert normalizer.normalize("  Manufactured   by   ABC   ") == "Manufactured by ABC"


def test_normalize_empty():
    assert normalizer.normalize("") == ""
    assert normalizer.normalize(None) == ""


def test_normalize_strips_noise_tokens():
    assert normalizer.normalize("---  MRP  Rs. 450") == "MRP Rs. 450"
    assert normalizer.normalize("hello [0:1] world") == "hello world"


def test_normalize_block_shape():
    b = normalizer.NormalizedBlock("Net  Wt. 500 g", 0.9, [1, 2, 3, 4])
    d = b.to_dict()
    assert d["normalized_text"] == "Net Wt. 500 g"
    assert d["confidence"] == 0.9
    assert d["bbox"] == [1, 2, 3, 4]


# ---------- Phase 6: line_builder ----------

def _block(text, y, x=0, h=20, w=80):
    return normalizer.NormalizedBlock(text, 0.9, [x, y, w, h])


def test_build_lines_groups_by_baseline():
    blocks = [
        _block("Manufactured", 10),
        _block("by", 100),  # far enough below -> its own line
        _block("ABC Foods", 10, x=120),  # same band as "Manufactured"
    ]
    lines = build_lines(blocks, image_height=1200)
    # "Manufactured" and "ABC Foods" are on the same band -> one line,
    # "by" is at a different y.
    assert len(lines) >= 2
    # the top line contains the two same-band blocks
    top = lines[0]
    assert top.text == "Manufactured ABC Foods"


def test_build_lines_left_to_right_ordering():
    blocks = [
        _block("B", 10, x=200),
        _block("A", 10, x=0),
        _block("C", 10, x=400),
    ]
    lines = build_lines(blocks, image_height=1200)
    assert lines[0].text == "A B C"


def test_join_lines():
    lines = [TextLine(text="line one", index=0, y=0), TextLine(text="line two", index=1, y=40)]
    assert join_lines(lines) == "line one\nline two"


def test_sort_lines_by_top():
    a = TextLine(text="second", index=0, y=100)
    b = TextLine(text="first", index=1, y=10)
    assert sort_lines_by_top([a, b])[0].text == "first"


from app.services.ocr.line_builder import sort_lines_by_top  # noqa: E402


# ---------- Phase 12: visualization ----------

def test_draw_ocr_boxes_shape():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    out = draw_ocr_boxes(img, [_block("hi", 10, x=5)], output_path="debug/test_boxes.png")
    assert out is not None
    assert out.shape[2] == 3


def test_draw_ocr_boxes_disabled_returns_input():
    # OCR_ENABLE_DEBUG is False by default and output_path None -> no-op
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    out = draw_ocr_boxes(img, [_block("hi", 10, x=5)])
    assert out.shape == img.shape