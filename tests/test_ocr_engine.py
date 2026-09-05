"""Tests for the Phase 4/5 single-pass OCR engine (app/services/ocr/engine.py).

Covers the evidence block contract (image_id, raw/normalized text, confidence,
bbox, engine), the lazy singleton reader, empty-image handling, and
backward-compatible array input. Does NOT assert any compliance outcome.
"""

from pathlib import Path

import numpy as np
import pytest

from app.services.image import preprocessing
from app.services.ocr import engine

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _tea_bgr() -> np.ndarray:
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        return preprocessing.decode(fh.read())


def test_engine_label_and_types():
    result = engine.run_ocr(_tea_bgr())
    assert result.engine == "easyocr"
    assert result.processing_time_ms >= 0
    assert isinstance(result.raw_text, str)
    assert isinstance(result.normalized_text, str)
    assert result.block_count == len(result.blocks)
    assert result.confidence_score >= 0.0
    assert result.confidence_score <= 1.0


def test_block_shape_and_traceability():
    result = engine.run_ocr(_tea_bgr(), image_id="img-1")
    assert result.blocks, "expected at least one block on the tea fixture"
    for block in result.blocks:
        assert block.image_id == "img-1"
        assert block.engine == "easyocr"
        assert isinstance(block.text, str) and block.text
        assert isinstance(block.raw_text, str) and block.raw_text
        assert block.normalized_text
        assert 0.0 <= block.confidence <= 1.0
        assert len(block.bbox) == 4
        assert block.bbox[0] >= 0 and block.bbox[1] >= 0
        assert block.bbox[2] >= 0 and block.bbox[3] >= 0


def test_block_preserves_verbatim_raw_text():
    result = engine.run_ocr(_tea_bgr())
    assert result.normalized_text == "\n".join(
        b.normalized_text for b in result.blocks
    )


def test_run_ocr_accepts_preprocessed_image():
    pre = preprocessing.preprocess(_tea_bgr())
    result = engine.run_ocr(pre, image_id="pre")
    for block in result.blocks:
        assert block.image_id == "pre"


def test_to_dict_shape():
    result = engine.run_ocr(_tea_bgr(), image_id="d")
    d = result.to_dict()
    assert set(d) >= {
        "blocks",
        "raw_text",
        "normalized_text",
        "confidence_score",
        "processing_time_ms",
        "engine",
        "block_count",
    }
    b0 = d["blocks"][0]
    assert set(b0) >= {"image_id", "raw_text", "normalized_text", "bbox", "engine"}
    assert isinstance(b0["confidence"], float)


def test_normalize_bbox():
    from app.services.ocr import normalize_bbox

    points = [[10, 20], [110, 20], [110, 60], [10, 60]]
    assert normalize_bbox(points) == [10, 20, 100, 40]


def test_normalize_bbox_empty():
    from app.services.ocr import normalize_bbox

    assert normalize_bbox([]) == [0, 0, 0, 0]


def test_blank_image_raises_no_text():
    blank = np.full((200, 200), 255, dtype=np.uint8)
    with pytest.raises(engine.OCRNoTextError) as exc:
        engine.run_ocr(blank)
    assert exc.value.code == engine.OCR_NO_TEXT


def test_empty_array_raises_ocr_failed():
    with pytest.raises(engine.OCREngineError) as exc:
        engine.run_ocr(np.zeros((0, 0), dtype=np.uint8))
    assert exc.value.code == engine.OCR_FAILED


def test_reader_is_cached_singleton():
    assert engine._get_reader() is engine._get_reader()