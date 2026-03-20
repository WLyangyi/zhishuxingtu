import sys
sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth_router, notes_router, folders_router, tags_router, search_router, graph_router, categories_router, contents_router, skills_router, prompts_router
from app.api.routes.few_shot import router as few_shot_router
from app.api.routes.ab_test import router as ab_test_router
from app.api.routes.prompt_eval import router as prompt_eval_router
from app.api.routes.prompt_chain import router as prompt_chain_router
from app.db.session import init_db
from app.services import init_vector_store, get_vector_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    faiss_path = settings.FAISS_INDEX_PATH
    init_vector_store(faiss_path)
    print(f"Vector store initialized at {faiss_path}")
    yield
    vector_store = get_vector_store()
    if vector_store:
        vector_store.save()
        print("Vector store saved")

app = FastAPI(
    title=settings.APP_NAME,
    description="个人知识库系统 API",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(prompts_router, prefix="/api")
app.include_router(few_shot_router, prefix="/api/prompts/few-shot", tags=["few-shot"])
app.include_router(ab_test_router, prefix="/api/ab-experiments", tags=["ab-test"])
app.include_router(prompt_eval_router, prefix="/api/prompt-evaluations", tags=["prompt-eval"])
app.include_router(prompt_chain_router, prefix="/api/prompt-chains", tags=["prompt-chain"])

@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
