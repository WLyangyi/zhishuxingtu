import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.note import Note
from app.services.embedding_service import embedding_service
from app.services.vector_store_adapter import get_vector_store_adapter
from app.core.config import settings


def rebuild_index_with_chunks():
    db: Session = SessionLocal()

    try:
        notes = db.query(Note).all()
        total = len(notes)

        if total == 0:
            print("No notes found in database.")
            return

        print(f"Found {total} notes to rebuild with chunking strategy.")
        print(f"Chunking config: max_size={settings.MAX_CHUNK_SIZE}, overlap={settings.OVERLAP_RATIO}")
        print()

        vector_store = get_vector_store_adapter()
        vector_store.clear()

        success_count = 0
        error_count = 0

        for i, note in enumerate(notes):
            try:
                if note.content:
                    chunks, vectors = embedding_service.embed_chunks(
                        note.id, note.title, note.content
                    )
                    if chunks and len(vectors) > 0:
                        vector_store.add_note_chunks(note.id, chunks, vectors)
                        success_count += 1
                        print(f"  [{i+1}/{total}] '{note.title}' -> {len(chunks)} chunks")
                    else:
                        print(f"  [{i+1}/{total}] '{note.title}' -> no chunks generated")
                else:
                    print(f"  [{i+1}/{total}] Note '{note.title}' has no content, skipping.")

                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{total}")

            except Exception as e:
                error_count += 1
                print(f"  Error processing note '{note.title}': {e}")

        vector_store.save()

        print(f"\nRebuild completed!")
        print(f"  Total notes: {total}")
        print(f"  Successfully vectorized: {success_count}")
        print(f"  Errors: {error_count}")

    except Exception as e:
        print(f"Rebuild failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting index rebuild with chunking strategy...")
    print()
    rebuild_index_with_chunks()