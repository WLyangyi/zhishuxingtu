from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import settings


class OCRError(RuntimeError):
    pass


@dataclass(frozen=True)
class OCRPage:
    index: int
    text: str
    finish_reason: str


@dataclass(frozen=True)
class OCRResult:
    id: str
    purpose: str
    page_count: int
    pages: list[OCRPage]
    usage: dict

    @property
    def non_empty_pages(self) -> list[OCRPage]:
        return [page for page in self.pages if page.text.strip()]

    @property
    def incomplete_pages(self) -> list[int]:
        return [page.index for page in self.pages if page.finish_reason == "length"]


class DeepSeekOCRClient:
    def recognize(self, file_path: str, page_count: int | None = None):
        if not settings.DEEPSEEK_API_KEY:
            raise OCRError("未配置 DEEPSEEK_API_KEY")
        if page_count is not None and page_count > settings.PDF_OCR_MAX_PAGES:
            raise OCRError(f"OCR 文档超过 {settings.PDF_OCR_MAX_PAGES} 页限制")
        file_size = Path(file_path).stat().st_size
        max_bytes = settings.PDF_OCR_MAX_FILE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise OCRError(f"OCR 文件超过 {settings.PDF_OCR_MAX_FILE_MB} MiB 限制")
        base = (settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com").rstrip("/")
        url = f"{base}/tools/ocr" if base.endswith("/v1") else f"{base}/v1/tools/ocr"
        for attempt in range(2):
            with open(file_path, "rb") as file:
                response = httpx.post(
                    url,
                    data={"purpose": "text_recognition"},
                    files={"file": (Path(file_path).name, file, "application/pdf")},
                    headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
                    timeout=settings.PDF_OCR_TIMEOUT,
                )
            try:
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if response.status_code in {429, 503} and attempt == 0:
                    continue
                try:
                    error = response.json().get("error", {})
                    message = error.get("message") if isinstance(error, dict) else str(error)
                except (ValueError, AttributeError):
                    message = ""
                raise OCRError(f"OCR HTTP {response.status_code}: {message or '请求失败'}") from exc
        payload = response.json()
        error = payload.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise OCRError(message or "OCR 识别失败")
        return OCRResult(
            id=payload.get("id", ""),
            purpose=payload.get("purpose", "text_recognition"),
            page_count=payload.get("page_count", 0),
            pages=[
                OCRPage(
                    index=page.get("index", 0),
                    text=page.get("text", ""),
                    finish_reason=page.get("finish_reason", "stop"),
                )
                for page in payload.get("pages", [])
            ],
            usage=payload.get("usage", {}),
        )
