import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.note import Note
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.core.config import settings


def migrate_notes_to_vectors():
    db: Session = SessionLocal()
    
    try:
        notes = db.query(Note).all()
        total = len(notes)
        
        if total == 0:
            print("No notes found in database.")
            return
        
        print(f"Found {total} notes to migrate.")
        
        faiss_path = settings.FAISS_INDEX_PATH
        os.makedirs(faiss_path, exist_ok=True)
        vector_store = VectorStore(faiss_path)
        
        success_count = 0
        error_count = 0
        
        for i, note in enumerate(notes):
            try:
                if note.content:
                    text = embedding_service.prepare_note_text(note.title, note.content)
                    vector = embedding_service.embed_text(text)
                    vector_store.add_vector(note.id, vector)
                    success_count += 1
                else:
                    print(f"  [{i+1}/{total}] Note '{note.title}' has no content, skipping.")
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{total}")
                    
            except Exception as e:
                error_count += 1
                print(f"  Error processing note '{note.title}': {e}")
        
        vector_store.save()
        
        print(f"\nMigration completed!")
        print(f"  Total notes: {total}")
        print(f"  Successfully vectorized: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  FAISS index saved to: {faiss_path}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting vector migration...")
    print(f"Embedding model: {getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L6-v2')}")
    print()
    migrate_notes_to_vectors()
