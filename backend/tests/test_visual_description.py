import json

import httpx
import pytest

from app.core.config import settings
from app.services.visual_description import VisualDescriptionClient, describe_page_safely


@pytest.fixture(autouse=True)
def _clear_visual_cache():
    from app.services import visual_description
    visual_description._description_cache.clear()
    yield
    visual_description._description_cache.clear()


def test_visual_description_request_sends_png_multimodal(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)

    VisualDescriptionClient().describe(b"\x89PNG\r\n\x1a\nimage", page_number=2)

    url, kwargs = calls[0]
    assert url == "https://api.deepseek.com/v1/chat/completions"
    content = kwargs["json"]["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_visual_request_prompt_mentions_json_for_json_mode(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    visual_description._description_cache.clear()

    VisualDescriptionClient().describe(b"png", page_number=1)

    prompt = calls[0]["json"]["messages"][0]["content"][0]["text"]
    assert "json" in prompt.lower()


def test_visual_request_uses_configured_visual_model(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "DEEPSEEK_MODEL", "chat-model")
    monkeypatch.setattr(settings, "VISUAL_MODEL", "visual-model")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    visual_description._description_cache.clear()

    VisualDescriptionClient().describe(b"png", page_number=1)

    assert calls[0]["json"]["model"] == "visual-model"


def test_visual_request_uses_configured_timeout(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "VISUAL_TIMEOUT", 123)
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    visual_description._description_cache.clear()

    VisualDescriptionClient().describe(b"png", page_number=1)

    assert calls[0]["timeout"] == 123


def test_visual_description_parses_structured_json(monkeypatch):
    payload = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "流程图描述",
                    "elements": ["开始", "结束"],
                    "relationships": ["开始指向结束"],
                    "uncertainties": ["颜色无法确认"],
                }, ensure_ascii=False)
            }
        }]
    }

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)

    result = VisualDescriptionClient().describe(b"png", page_number=1)

    assert result.summary == "流程图描述"
    assert result.elements == ["开始", "结束"]
    assert result.uncertainties == ["颜色无法确认"]


def test_visual_description_failure_is_isolated(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            503,
            json={"error": {"message": "服务繁忙"}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)

    description, error = describe_page_safely(b"png", page_number=1)

    assert description is None
    assert "503" in error


def test_visual_description_is_cached_by_image_and_page(monkeypatch):
    calls = []
    payload = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "缓存描述",
                    "elements": [],
                    "relationships": [],
                    "uncertainties": [],
                }, ensure_ascii=False)
            }
        }]
    }

    def fake_post(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test")
    from app.services import visual_description
    monkeypatch.setattr(visual_description.httpx, "post", fake_post)
    visual_description._description_cache.clear()
    client = VisualDescriptionClient()

    client.describe(b"same-png", page_number=1)
    client.describe(b"same-png", page_number=1)

    assert len(calls) == 1
