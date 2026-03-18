import sys
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth_router, notes_router, folders_router, tags_router, search_router, graph_router, categories_router, contents_router, skills_router
from app.db.session import init_db

app = FastAPI(
    title=settings.APP_NAME,
    description="个人知识库系统 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(contents_router, prefix="/api")
app.include_router(skills_router, prefix="/api")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
