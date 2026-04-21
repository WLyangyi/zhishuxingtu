import os


class PDFParseError(Exception):
    pass


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
            doc.close()
            raise
        except Exception as e:
            doc.close()
            raise PDFParseError(f"解析 PDF 时出错: {str(e)}")

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
