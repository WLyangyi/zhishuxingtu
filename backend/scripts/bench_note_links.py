"""500 篇规模下对比图谱出链的两种读法：逐篇 json.loads vs 关联表一次查询。

运行方式(backend 目录下):
  .venv\\Scripts\\python.exe scripts\\bench_note_links.py
仅作 P1-1 验收参考，不写入任何真实数据库。
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.models.note import Note  # noqa: E402
from app.models.note_link import NoteLink  # noqa: E402
from app.models.user import User  # noqa: E402

N = 500
ROUNDS = 20

engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()
db.add(User(id="u", username="u", password_hash="x"))

ids = [f"n{i}" for i in range(N)]
notes = [
    Note(
        id=note_id,
        title=note_id,
        user_id="u",
        linked_note_ids=json.dumps([ids[(idx + 1) % N] for idx in range(i % 4 + 1)]),
    )
    for i, note_id in enumerate(ids)
]
db.add_all(notes)
db.commit()
db.add_all([NoteLink(source_id=note_id, target_id=ids[(i + 1) % N]) for i, note_id in enumerate(ids)])
db.commit()

start = time.perf_counter()
for _ in range(ROUNDS):
    for note in notes:
        json.loads(note.linked_note_ids or "[]")
old_ms = (time.perf_counter() - start) * 1000

start = time.perf_counter()
for _ in range(ROUNDS):
    db.query(NoteLink.source_id, NoteLink.target_id).filter(NoteLink.source_id.in_(ids)).all()
new_ms = (time.perf_counter() - start) * 1000

print(f"{N} 篇 × {ROUNDS} 轮：旧 JSON 解析 {old_ms:.1f}ms；新关联表查询 {new_ms:.1f}ms；比值 {old_ms / new_ms:.2f}x")
