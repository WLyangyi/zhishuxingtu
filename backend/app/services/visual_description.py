import base64
import hashlib
import json
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

VISUAL_PROMPT_VERSION = "v1"
_description_cache = {}


@dataclass(frozen=True)
class VisualDescription:
    summary: str
    elements: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)


class VisualDescriptionClient:
    def describe(self, png: bytes, page_number: int):
        base = (settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com").rstrip("/")
        url = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
        image_url = f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"
        cache_key = (
            hashlib.sha256(png).hexdigest(),
            page_number,
            settings.VISUAL_MODEL,
            VISUAL_PROMPT_VERSION,
        )
        if cache_key in _description_cache:
            return _description_cache[cache_key]
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": settings.VISUAL_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"请描述第 {page_number} 页中的图表、流程图或版式关系，只依据原图，不确定的细节明确说明。"
                                "请以 JSON 返回，字段为 summary、elements、relationships、uncertainties。"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }],
                "response_format": {"type": "json_object"},
                "stream": False,
            },
            timeout=settings.VISUAL_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        description = json.loads(content)
        result = VisualDescription(
            summary=description.get("summary", ""),
            elements=description.get("elements", []),
            relationships=description.get("relationships", []),
            uncertainties=description.get("uncertainties", []),
        )
        _description_cache[cache_key] = result
        return result


def describe_page_safely(png: bytes, page_number: int) -> tuple[VisualDescription | None, str]:
    try:
        return VisualDescriptionClient().describe(png, page_number), ""
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        return None, str(exc)
