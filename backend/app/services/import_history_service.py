from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.import_history import ImportHistory


class ImportHistoryService:
    def create_record(
        self,
        db: Session,
        user_id: str,
        task_id: str,
        source_type: str,
        source_url: Optional[str] = None,
        source_filename: Optional[str] = None,
        duration: Optional[int] = None,
        platform: Optional[str] = None,
        generated_title: Optional[str] = None,
        note_id: Optional[str] = None,
        status: str = "completed"
    ) -> ImportHistory:
        record = ImportHistory(
            user_id=user_id,
            task_id=task_id,
            source_type=source_type,
            source_url=source_url,
            source_filename=source_filename,
            duration=duration,
            platform=platform,
            generated_title=generated_title,
            note_id=note_id,
            status=status
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_history(
        self,
        db: Session,
        user_id: str,
        source_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple:
        query = db.query(ImportHistory).filter(ImportHistory.user_id == user_id)

        if source_type:
            query = query.filter(ImportHistory.source_type == source_type)

        query = query.order_by(ImportHistory.created_at.desc())

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return items, total

    def update_note_id(self, db: Session, task_id: str, note_id: str) -> Optional[ImportHistory]:
        record = db.query(ImportHistory).filter(ImportHistory.task_id == task_id).first()
        if record:
            record.note_id = note_id
            db.commit()
            db.refresh(record)
        return record

    def get_by_task_id(self, db: Session, task_id: str) -> Optional[ImportHistory]:
        return db.query(ImportHistory).filter(ImportHistory.task_id == task_id).first()


_import_history_service_instance = None


def get_import_history_service() -> ImportHistoryService:
    global _import_history_service_instance
    if _import_history_service_instance is None:
        _import_history_service_instance = ImportHistoryService()
    return _import_history_service_instance
