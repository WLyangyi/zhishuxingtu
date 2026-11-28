import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VisualAssetFile:
    path: Path
    sha256: str
    mime_type: str = "image/png"


class VisualAssetStore:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def save(self, user_id: str, note_id: str, page_number: int, png: bytes) -> VisualAssetFile:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", user_id):
            raise ValueError("非法 user_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", note_id):
            raise ValueError("非法 note_id")
        if page_number < 1:
            raise ValueError("page_number 必须大于 0")
        path = self.root_dir / user_id / note_id / f"page-{page_number}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
        return VisualAssetFile(
            path=path,
            sha256=hashlib.sha256(png).hexdigest(),
            mime_type="image/png",
        )
