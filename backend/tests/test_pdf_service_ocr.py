import fitz
import httpx
import pytest
from PIL import Image, ImageDraw

from app.core.config import settings
from app.services.deepseek_ocr import DeepSeekOCRClient
from app.services.pdf_service import PDFParseError, PDFService


def test_text_pdf_auto_mode_uses_pymupdf_without_ocr(monkeypatch, tmp_path):
    pdf = tmp_path / "text.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "hello OCR")
        doc.save(pdf)

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(
        DeepSeekOCRClient,
        "recognize",
        lambda *args, **kwargs: pytest.fail("文字型 PDF 不应调用 OCR"),
    )

    result = PDFService().extract_document(str(pdf))

    assert result.source == "pymupdf"
    assert result.page_count == 1
    assert "hello OCR" in result.text


def test_image_only_pdf_auto_mode_uses_deepseek_ocr(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    image_path = tmp_path / "page.png"
    image = Image.new("RGB", (600, 800), "white")
    ImageDraw.Draw(image).text((72, 72), "scaned text", fill="black")
    image.save(image_path)
    pdf = tmp_path / "scan.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=800)
        page.insert_image(page.rect, filename=image_path)
        doc.save(pdf)

    payload = {
        "page_count": 1,
        "pages": [{"index": 0, "text": "OCR 正文", "finish_reason": "stop"}],
    }
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)

    result = PDFService().extract_document(str(pdf))

    assert result.source == "deepseek_ocr"
    assert result.page_count == 1
    assert "OCR 正文" in result.text
    assert len(calls) == 1


def test_force_mode_ocrs_text_pdf(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "text.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "已有文本层")
        doc.save(pdf)
    payload = {
        "page_count": 1,
        "pages": [{"index": 0, "text": "强制 OCR 正文", "finish_reason": "stop"}],
    }
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "force")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)

    result = PDFService().extract_document(str(pdf))

    assert result.source == "deepseek_ocr"
    assert "强制 OCR 正文" in result.text
    assert len(calls) == 1


def test_off_mode_rejects_scan_without_ocr(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    Image.new("RGB", (300, 300), "white").save(image_path)
    pdf = tmp_path / "scan.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=300, height=300)
        page.insert_image(page.rect, filename=image_path)
        doc.save(pdf)
    monkeypatch.setattr(settings, "PDF_OCR_MODE", "off")

    with pytest.raises(PDFParseError, match="OCR 已关闭"):
        PDFService().extract_document(str(pdf))


def test_ocr_text_is_sorted_and_marked_by_page(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {
        "page_count": 2,
        "pages": [
            {"index": 1, "text": "第二页", "finish_reason": "stop"},
            {"index": 0, "text": "第一页", "finish_reason": "stop"},
        ],
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "force")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)

    result = PDFService().extract_document(str(pdf))

    assert result.text.index("[第 1 页]") < result.text.index("[第 2 页]")


def test_ocr_text_marks_incomplete_page(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {
        "page_count": 1,
        "pages": [{"index": 0, "text": "部分正文", "finish_reason": "length"}],
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "force")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)

    result = PDFService().extract_document(str(pdf))

    assert "该页输出不完整" in result.text
