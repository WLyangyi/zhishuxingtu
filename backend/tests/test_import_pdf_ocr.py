import asyncio
import json

import fitz
import httpx
import pytest
from PIL import Image

from app.core.config import settings
from app.services import import_orchestrator
from app.services.import_orchestrator import PDFImportOrchestrator
from app.services.import_task_store import get_import_task_store


def test_pdf_orchestrator_uses_ocr_extraction(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    image_path = tmp_path / "page.png"
    Image.new("RGB", (300, 300), "white").save(image_path)
    pdf = tmp_path / "scan.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=300, height=300)
        page.insert_image(page.rect, filename=image_path)
        doc.save(pdf)

    payload = {
        "page_count": 1,
        "pages": [{"index": 0, "text": "OCR 正文", "finish_reason": "stop"}],
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    class FakeSummarizer:
        def summarize(self, text, source_type):
            return {"title": "扫描件", "summary": "摘要", "key_points": [], "tags": []}

    monkeypatch.setattr(import_orchestrator, "get_summarizer_service", lambda: FakeSummarizer())
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf", source_path=str(pdf))
    orchestrator = PDFImportOrchestrator(task, str(pdf), "scan.pdf")

    asyncio.run(orchestrator.execute())

    assert task.status == "completed"
    assert "OCR 正文" in task.extracted_content
    task_store.delete_task(task.task_id)


def test_ocr_failure_keeps_domain_error_in_task(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    image_path = tmp_path / "page.png"
    Image.new("RGB", (300, 300), "white").save(image_path)
    pdf = tmp_path / "scan.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=300, height=300)
        page.insert_image(page.rect, filename=image_path)
        doc.save(pdf)

    def fake_post(url, **kwargs):
        return httpx.Response(
            402,
            json={"error": {"message": "余额不足"}},
            request=httpx.Request("POST", url),
        )

    class FakeSummarizer:
        def summarize(self, text, source_type):
            pytest.fail("OCR 失败时不应进入摘要生成")

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(import_orchestrator, "get_summarizer_service", lambda: FakeSummarizer())
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf", source_path=str(pdf))
    orchestrator = PDFImportOrchestrator(task, str(pdf), "scan.pdf")

    asyncio.run(orchestrator.execute())

    assert task.status == "failed"
    assert task.error.startswith("OCR HTTP 402")
    task_store.delete_task(task.task_id)


def test_pdf_import_appends_visual_description(monkeypatch, tmp_path):
    from app.services import visual_description

    image_path = tmp_path / "chart.png"
    Image.new("RGB", (200, 120), "white").save(image_path)
    pdf = tmp_path / "visual.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((72, 72), "正文")
        page.insert_image(fitz.Rect(200, 50, 350, 150), filename=image_path)
        doc.save(pdf)
    payload = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "图表描述",
                    "elements": [],
                    "relationships": [],
                    "uncertainties": [],
                }, ensure_ascii=False)
            }
        }]
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    class FakeSummarizer:
        def summarize(self, text, source_type):
            return {"title": "视觉文档", "summary": "摘要", "key_points": [], "tags": []}

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(settings, "VISUAL_EVIDENCE_ENABLED", True)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    monkeypatch.setattr(visual_description, "_description_cache", {})
    monkeypatch.setattr(import_orchestrator, "get_summarizer_service", lambda: FakeSummarizer())
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf", source_path=str(pdf))
    orchestrator = PDFImportOrchestrator(task, str(pdf), "visual.pdf")

    asyncio.run(orchestrator.execute())

    assert task.status == "completed"
    assert "[视觉描述-第 1 页]" in task.extracted_content
    assert "图表描述" in task.extracted_content
    assert len(task.visual_assets) == 1
    assert task.visual_assets[0]["png"].startswith(b"\x89PNG")
    assert task.visual_assets[0]["description"] == "图表描述"
    task_store.delete_task(task.task_id)


def test_visual_calls_respect_page_limit_even_after_failures(monkeypatch, tmp_path):
    from app.services import visual_description

    image_path = tmp_path / "chart.png"
    Image.new("RGB", (100, 80), "white").save(image_path)
    pdf = tmp_path / "visual.pdf"
    with fitz.open() as doc:
        for _ in range(5):
            page = doc.new_page(width=300, height=200)
            page.insert_text((20, 20), "正文")
            page.insert_image(fitz.Rect(100, 50, 200, 120), filename=image_path)
        doc.save(pdf)
    calls = []
    payload = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "描述",
                    "elements": [],
                    "relationships": [],
                    "uncertainties": [],
                }, ensure_ascii=False)
            }
        }]
    }

    def fake_post(url, **kwargs):
        calls.append(url)
        if len(calls) <= 2:
            return httpx.Response(
                503,
                json={"error": {"message": "服务繁忙"}},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    class FakeSummarizer:
        def summarize(self, text, source_type):
            return {"title": "视觉文档", "summary": "摘要", "key_points": [], "tags": []}

    monkeypatch.setattr(settings, "PDF_OCR_MODE", "auto")
    monkeypatch.setattr(settings, "VISUAL_EVIDENCE_ENABLED", True)
    monkeypatch.setattr(settings, "VISUAL_MAX_PAGES_PER_DOC", 3)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    monkeypatch.setattr(visual_description, "_description_cache", {})
    monkeypatch.setattr(import_orchestrator, "get_summarizer_service", lambda: FakeSummarizer())
    task_store = get_import_task_store()
    task = task_store.create_task(user_id="u1", source_type="pdf", source_path=str(pdf))
    orchestrator = PDFImportOrchestrator(task, str(pdf), "visual.pdf")

    asyncio.run(orchestrator.execute())

    assert len(calls) == 3
    task_store.delete_task(task.task_id)
