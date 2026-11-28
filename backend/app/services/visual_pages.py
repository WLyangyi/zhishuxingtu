from dataclasses import dataclass

import fitz

VECTOR_MIN_PATHS = 40
VECTOR_MIN_FILLS = 20


@dataclass(frozen=True)
class VisualPageCandidate:
    page_index: int
    reasons: list[str]
    image_count: int
    drawing_count: int


def detect_visual_pages(page, page_index: int) -> list[VisualPageCandidate]:
    images = page.get_images(full=True)
    drawings = page.get_drawings()
    fill_count = sum(1 for drawing in drawings if "f" in drawing.get("type", ""))
    complex_vector = len(drawings) >= VECTOR_MIN_PATHS and fill_count >= VECTOR_MIN_FILLS
    if not images and not complex_vector:
        return []
    reasons = []
    if images:
        reasons.append("embedded_image")
    if complex_vector:
        reasons.append("complex_vector")
    return [
        VisualPageCandidate(
            page_index=page_index,
            reasons=reasons,
            image_count=len(images),
            drawing_count=len(drawings),
        )
    ]


def render_visual_page(page) -> bytes:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pixmap.tobytes("png")
