import re
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRBlock:
    page: int
    text: str
    bbox: list[float]
    confidence: float = 1.0


_BLOCK_PATTERN = re.compile(
    r"<｜?ref｜?>(.*?)<｜?/?ref｜?>\s*<｜?box｜?>\s*\[\[(.*?)\]\]\s*<｜?/?box｜?>",
    re.DOTALL,
)


def clean_ocr_text(text: str) -> str:
    text = re.sub(r"<｜?/?ref｜?>", "", text)
    return re.sub(r"<｜?box｜?>.*?<｜?/?box｜?>", "", text, flags=re.DOTALL)


def parse_ocr_blocks(text: str, page_index: int = 0) -> list[OCRBlock]:
    blocks = []
    for match in _BLOCK_PATTERN.finditer(text):
        block_text = match.group(1).strip()
        try:
            bbox = [float(value.strip()) for value in match.group(2).split(",")]
        except ValueError:
            continue
        if len(bbox) != 4 or any(value < 0 or value > 1000 for value in bbox):
            continue
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            continue
        if block_text:
            blocks.append(OCRBlock(page=page_index, text=block_text, bbox=bbox))
    return blocks
