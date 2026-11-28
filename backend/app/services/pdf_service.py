import os
from dataclasses import dataclass

from app.core.config import settings
from app.services.deepseek_ocr import DeepSeekOCRClient
from app.services.ocr_layout import clean_ocr_text


class PDFParseError(Exception):
    pass


@dataclass(frozen=True)
class PDFExtractionResult:
    text: str
    page_count: int
    source: str


class PDFService:
    def __init__(self):
        self._fitz = None

    def _get_fitz(self):
        if self._fitz is None:
            try:
                import fitz
                self._fitz = fitz
            except ImportError:
                raise PDFParseError("pymupdf 未安装，请运行: pip install pymupdf")
        return self._fitz

    def extract_text(self, file_path: str, max_chars: int = 50000) -> str:
        fitz = self._get_fitz()

        if not os.path.exists(file_path):
            raise PDFParseError("文件不存在")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypt" in error_msg or "password" in error_msg:
                raise PDFParseError("PDF 已加密，请先解密")
            raise PDFParseError(f"文件损坏，无法解析: {str(e)}")

        try:
            if doc.is_encrypted:
                raise PDFParseError("PDF 已加密，请先解密")

            total_pages = len(doc)
            if total_pages == 0:
                raise PDFParseError("PDF 为空")

            text_parts = []
            total_chars = 0

            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text("text")

                if page_text.strip():
                    text_parts.append(page_text)
                    total_chars += len(page_text)

                if total_chars >= max_chars:
                    break

            doc.close()

            full_text = "\n".join(text_parts)

            if not full_text.strip():
                raise PDFParseError("无法识别文字，可能是扫描版 PDF")

            if len(full_text) > max_chars:
                full_text = full_text[:max_chars] + "\n\n[内容已截断，原文过长]"

            return full_text

        except PDFParseError:
            if not doc.is_closed:
                doc.close()
            raise
        except Exception as e:
            if not doc.is_closed:
                doc.close()
            raise PDFParseError(f"解析 PDF 时出错: {str(e)}")

    def extract_document(self, file_path: str) -> PDFExtractionResult:
        if settings.PDF_OCR_MODE == "force":
            return self._extract_with_ocr(file_path)
        try:
            text = self.extract_text(file_path)
        except PDFParseError as exc:
            if "无法识别文字" in str(exc) and settings.PDF_OCR_MODE == "off":
                raise PDFParseError("OCR 已关闭，无法识别扫描版 PDF") from exc
            if settings.PDF_OCR_MODE != "auto" or "无法识别文字" not in str(exc):
                raise
            return self._extract_with_ocr(file_path)
        return PDFExtractionResult(
            text=text,
            page_count=self.get_page_count(file_path),
            source="pymupdf",
        )

    def _extract_with_ocr(self, file_path: str) -> PDFExtractionResult:
        page_count = self.get_page_count(file_path)
        result = DeepSeekOCRClient().recognize(file_path, page_count=page_count)
        parts = []
        for page in sorted(result.non_empty_pages, key=lambda item: item.index):
            notice = "\n[该页输出不完整]" if page.finish_reason == "length" else ""
            parts.append(f"[第 {page.index + 1} 页]\n{clean_ocr_text(page.text)}{notice}")
        text = "\n\n".join(parts)
        if not text.strip():
            raise PDFParseError("OCR 未识别到文字")
        return PDFExtractionResult(text=text, page_count=page_count, source="deepseek_ocr")

    def get_page_count(self, file_path: str) -> int:
        fitz = self._get_fitz()
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0


_pdf_service_instance = None


def get_pdf_service() -> PDFService:
    global _pdf_service_instance
    if _pdf_service_instance is None:
        _pdf_service_instance = PDFService()
    return _pdf_service_instance
