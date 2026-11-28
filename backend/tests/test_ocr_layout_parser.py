import pytest

from app.services.ocr_layout import clean_ocr_text, parse_ocr_blocks


@pytest.mark.parametrize(
    "raw",
    [
        "<ref>标题</ref><box>[[52, 40, 948, 96]]</box>正文",
        "<｜ref｜>标题<｜/ref｜><｜box｜>[[52, 40, 948, 96]]<｜/box｜>正文",
    ],
)
def test_clean_ocr_text_removes_layout_markers(raw):
    assert clean_ocr_text(raw) == "标题正文"


def test_parse_ocr_blocks_extracts_text_and_bbox():
    raw = "<ref>标题</ref><box>[[52, 40, 948, 96]]</box>"

    blocks = parse_ocr_blocks(raw, page_index=2)

    assert len(blocks) == 1
    assert blocks[0].page == 2
    assert blocks[0].text == "标题"
    assert blocks[0].bbox == [52.0, 40.0, 948.0, 96.0]
    assert blocks[0].confidence == 1.0


@pytest.mark.parametrize("coords", ["a,b,c,d", "-1,40,948,96"])
def test_invalid_bbox_is_ignored(coords):
    raw = f"<ref>标题</ref><box>[[{coords}]]</box>"

    assert parse_ocr_blocks(raw) == []
