import httpx
import pytest

from app.core.config import Settings, settings


@pytest.fixture(autouse=True)
def _isolate_ocr_settings(monkeypatch):
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def test_pdf_ocr_mode_defaults_to_auto():
    mode = getattr(settings, "PDF_OCR_MODE", None)
    assert mode == "auto"


def test_pdf_ocr_timeout_defaults_to_240_seconds():
    timeout = getattr(settings, "PDF_OCR_TIMEOUT", None)
    assert timeout == 240


def test_pdf_ocr_max_file_defaults_to_100_mib():
    limit = getattr(settings, "PDF_OCR_MAX_FILE_MB", None)
    assert limit == 100


def test_pdf_ocr_max_pages_defaults_to_1000():
    limit = getattr(settings, "PDF_OCR_MAX_PAGES", None)
    assert limit == 1000


def test_invalid_pdf_ocr_mode_falls_back_to_auto():
    configured = Settings(PDF_OCR_MODE="bogus")
    assert configured.PDF_OCR_MODE == "auto"


def test_ocr_request_uses_multipart_endpoint(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"pages": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    url, kwargs = calls[0]
    assert url == "https://api.deepseek.com/v1/tools/ocr"
    assert kwargs["data"] == {"purpose": "text_recognition"}
    assert kwargs["files"]["file"][0] == "scan.pdf"


def test_ocr_requires_deepseek_api_key_before_network(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "")
    monkeypatch.setattr(
        deepseek_ocr.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("缺密钥时不应发起网络请求"),
    )

    with pytest.raises(deepseek_ocr.OCRError, match="DEEPSEEK_API_KEY"):
        deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))


def test_ocr_request_uses_configured_timeout(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, json={"pages": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "PDF_OCR_TIMEOUT", 123)

    deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert calls[0]["timeout"] == 123


def test_ocr_request_reuses_deepseek_api_key(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"pages": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-existing")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert calls[0][1]["headers"]["Authorization"] == "Bearer sk-existing"


def test_ocr_response_parses_pages_and_finish_reason(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {
        "id": "ocr-1",
        "object": "ocr.result",
        "created": 1762790000,
        "purpose": "text_recognition",
        "page_count": 2,
        "pages": [
            {"index": 0, "text": "第一页", "finish_reason": "stop"},
            {"index": 1, "text": "第二页", "finish_reason": "length"},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")

    result = deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert result.page_count == 2
    assert result.pages[0].text == "第一页"
    assert result.pages[1].finish_reason == "length"
    assert result.usage["total_tokens"] == 30


def test_ocr_result_excludes_empty_text_pages(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {
        "page_count": 2,
        "pages": [
            {"index": 0, "text": "  ", "finish_reason": "stop"},
            {"index": 1, "text": "正文", "finish_reason": "stop"},
        ],
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)

    result = deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert [page.index for page in result.non_empty_pages] == [1]


def test_ocr_result_marks_incomplete_pages(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {
        "page_count": 2,
        "pages": [
            {"index": 0, "text": "完整", "finish_reason": "stop"},
            {"index": 1, "text": "截断", "finish_reason": "length"},
        ],
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")

    result = deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert result.incomplete_pages == [1]


def test_ocr_200_error_body_is_not_treated_as_success(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    payload = {"error": {"message": "余额不足", "type": "insufficient_quota"}}

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")

    with pytest.raises(deepseek_ocr.OCRError, match="余额不足"):
        deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))


@pytest.mark.parametrize("status", [402, 413])
def test_nonretryable_http_errors_are_not_retried(monkeypatch, tmp_path, status):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return httpx.Response(
            status,
            json={"error": {"message": "不可重试"}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")

    with pytest.raises(deepseek_ocr.OCRError, match=str(status)):
        deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert len(calls) == 1


def test_ocr_rejects_oversized_file_before_network(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "large.pdf"
    with pdf.open("wb") as file:
        file.truncate(2 * 1024 * 1024)
    monkeypatch.setattr(settings, "PDF_OCR_MAX_FILE_MB", 1)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        deepseek_ocr.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("超限文件不应发起网络请求"),
    )

    with pytest.raises(deepseek_ocr.OCRError, match="MiB"):
        deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))


def test_ocr_rejects_too_many_pages_before_network(monkeypatch, tmp_path):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    monkeypatch.setattr(settings, "PDF_OCR_MAX_PAGES", 2)
    monkeypatch.setattr(
        deepseek_ocr.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("超页数文件不应发起网络请求"),
    )

    with pytest.raises(deepseek_ocr.OCRError, match="页"):
        deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf), page_count=3)


@pytest.mark.parametrize("status", [429, 503])
def test_temporary_http_errors_retry_once(monkeypatch, tmp_path, status):
    from app.services import deepseek_ocr

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return httpx.Response(
                status,
                json={"error": {"message": "稍后重试"}},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(
            200,
            json={"page_count": 1, "pages": [{"index": 0, "text": "成功", "finish_reason": "stop"}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(deepseek_ocr.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")

    result = deepseek_ocr.DeepSeekOCRClient().recognize(str(pdf))

    assert result.page_count == 1
    assert len(calls) == 2
