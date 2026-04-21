import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List


@dataclass
class VideoInfo:
    duration: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    audio_tracks: int = 0
    subtitle_tracks: int = 0
    platform: Optional[str] = None


@dataclass
class SourceInfo:
    type: str = ""
    url: Optional[str] = None
    filename: Optional[str] = None
    duration: Optional[int] = None
    platform: Optional[str] = None
    imported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ImportResult:
    title: str = ""
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_info: Optional[SourceInfo] = None


@dataclass
class ImportTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    source_type: str = ""
    source_path: str = ""
    status: str = "pending"
    progress: int = 0
    progress_message: str = ""
    extracted_content: str = ""
    video_info: Optional[VideoInfo] = None
    result: Optional[ImportResult] = None
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ImportTaskStore:
    def __init__(self):
        self._tasks: Dict[str, ImportTask] = {}
        self._lock = threading.Lock()

    def create_task(self, user_id: str, source_type: str, source_path: str = "") -> ImportTask:
        task = ImportTask(
            user_id=user_id,
            source_type=source_type,
            source_path=source_path,
            status="pending",
            progress=0,
            progress_message="任务已创建"
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ImportTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[ImportTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.utcnow().isoformat()
            return task

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def get_tasks_by_user(self, user_id: str) -> List[ImportTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.user_id == user_id]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        with self._lock:
            to_delete = []
            for task_id, task in self._tasks.items():
                try:
                    task_time = datetime.fromisoformat(task.created_at).timestamp()
                    if task_time < cutoff:
                        to_delete.append(task_id)
                except (ValueError, TypeError):
                    to_delete.append(task_id)
            for task_id in to_delete:
                del self._tasks[task_id]


_import_task_store_instance = None


def get_import_task_store() -> ImportTaskStore:
    global _import_task_store_instance
    if _import_task_store_instance is None:
        _import_task_store_instance = ImportTaskStore()
    return _import_task_store_instance
