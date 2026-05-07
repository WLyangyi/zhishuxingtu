import os
import shutil
import uuid
from app.core.config import settings

TEMP_DIR = getattr(settings, 'IMPORT_TEMP_DIR', './temp/imports')


def ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


def save_temp_file(content: bytes, filename: str, task_id: str = None) -> str:
    ensure_temp_dir()
    if not task_id:
        task_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{task_id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def cleanup_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


def cleanup_temp_dir(dir_path: str):
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    except Exception:
        pass
