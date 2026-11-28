import base64
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.models import ImportVisualAsset


def build_visual_evidence_messages(db, user_id: str, documents: list[dict], max_images: int = 3) -> list[HumanMessage]:
    note_ids = list(dict.fromkeys(
        doc.get("id") for doc in documents or []
        if isinstance(doc, dict) and isinstance(doc.get("id"), str)
    ))
    if not note_ids or max_images <= 0:
        return []
    assets = db.query(ImportVisualAsset).filter(
        ImportVisualAsset.user_id == user_id,
        ImportVisualAsset.note_id.in_(note_ids),
    ).order_by(ImportVisualAsset.note_id, ImportVisualAsset.page_number).limit(max_images).all()
    if not assets:
        return []

    descriptions = []
    image_blocks = []
    for asset in assets:
        path = Path(asset.image_path)
        source = asset.source_filename or asset.note_id
        if not path.is_file():
            descriptions.append(
                f"来源#{asset.note_id}（{source}，第 {asset.page_number} 页）："
                "未提供原图，仅有视觉描述；无法对照原图核实。"
            )
            continue
        descriptions.append(
            f"来源#{asset.note_id}（{source}，第 {asset.page_number} 页）："
            f"{asset.description or '未提供视觉描述'}"
        )
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        image_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:{asset.mime_type};base64,{encoded}"},
        })
    if not descriptions:
        return []
    text = (
        "以下是检索命中的原图证据。请对照原图核实视觉描述；"
        "无法从原图确认的细节必须明确说明，不得把视觉描述当作原文。\n"
        + "\n".join(descriptions)
    )
    return [HumanMessage(content=[{"type": "text", "text": text}, *image_blocks])]


def collect_visual_evidence_metadata(db, user_id: str, documents: list[dict], max_images: int = 3) -> list[dict]:
    note_ids = list(dict.fromkeys(
        doc.get("id") for doc in documents or []
        if isinstance(doc, dict) and isinstance(doc.get("id"), str)
    ))
    if not note_ids or max_images <= 0:
        return []
    assets = db.query(ImportVisualAsset).filter(
        ImportVisualAsset.user_id == user_id,
        ImportVisualAsset.note_id.in_(note_ids),
    ).order_by(ImportVisualAsset.note_id, ImportVisualAsset.page_number).limit(max_images).all()
    return [
        {
            "asset_id": asset.id,
            "note_id": asset.note_id,
            "page_number": asset.page_number,
            "source_filename": asset.source_filename or "",
            "description": asset.description or "",
            "description_status": asset.description_status,
            "image_url": f"/api/import/notes/{asset.note_id}/assets/{asset.id}/image",
        }
        for asset in assets
    ]
