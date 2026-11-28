from io import BytesIO

import fitz
from PIL import Image

from app.services.visual_pages import detect_visual_pages, render_visual_page


def test_page_with_embedded_image_is_visual_candidate(tmp_path):
    image_path = tmp_path / "chart.png"
    Image.new("RGB", (200, 120), "white").save(image_path)
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_image(page.rect, filename=image_path)

        candidates = detect_visual_pages(page, page_index=0)

    assert len(candidates) == 1
    assert candidates[0].page_index == 0
    assert "embedded_image" in candidates[0].reasons


def test_complex_vector_page_is_visual_candidate():
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for index in range(25):
            x = (index % 5) * 70
            y = (index // 5) * 50
            page.draw_rect(fitz.Rect(x, y, x + 50, y + 30), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
        for index in range(20):
            x = (index % 5) * 70
            y = (index // 5) * 50
            page.draw_line(fitz.Point(x, y), fitz.Point(x + 50, y + 30))

        candidates = detect_visual_pages(page, page_index=0)

    assert len(candidates) == 1
    assert "complex_vector" in candidates[0].reasons


def test_render_visual_page_returns_fixed_scale_png():
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((72, 72), "visual")

        png = render_visual_page(page)

    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(png)) as image:
        assert image.size == (800, 600)


def test_simple_vector_page_is_not_visual_candidate():
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for index in range(8):
            page.draw_rect(fitz.Rect(20, 20 + index * 20, 380, 30 + index * 20), fill=(0.9, 0.9, 0.9))

        assert detect_visual_pages(page, page_index=0) == []


def test_render_visual_page_is_deterministic():
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((72, 72), "visual")

        assert render_visual_page(page) == render_visual_page(page)
