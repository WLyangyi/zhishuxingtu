import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.routes import auth_router, notes_router, folders_router, tags_router, search_router, graph_router, categories_router, contents_router, skills_router, prompts_router, import_router, agent_router
from app.api.routes.few_shot import router as few_shot_router
from app.api.routes.ab_test import router as ab_test_router
from app.api.routes.prompt_eval import router as prompt_eval_router
from app.api.routes.prompt_chain import router as prompt_chain_router
from app.db.session import init_db
from app.services import init_vector_store, get_vector_store, init_hybrid_search
from app.services.mcp_server import MCPAuthMiddleware, create_mcp_server

limiter = Limiter(key_func=get_remote_address)

# M3: MCP Server（FastMCP）— Streamable HTTP 子应用，挂载见 app.mount("/mcp", ...)
mcp_app = create_mcp_server().http_app(path="/", transport="http")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY 未正确配置，请检查 .env 文件")
    if not settings.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY 未正确配置，请检查 .env 文件")

    init_db()
    faiss_path = settings.FAISS_INDEX_PATH
    init_vector_store(faiss_path)
    print(f"Vector store initialized at {faiss_path}")

    if settings.USE_HYBRID_SEARCH:
        init_hybrid_search()
        print("Hybrid search service initialized (BM25 + Vector)")

    # M3: 接管 FastMCP session manager 的生命周期（挂载的子应用 lifespan 不会自动执行）
    async with mcp_app.lifespan(mcp_app):
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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
app.include_router(import_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(few_shot_router, prefix="/api/prompts/few-shot", tags=["few-shot"])
app.include_router(ab_test_router, prefix="/api/ab-experiments", tags=["ab-test"])
app.include_router(prompt_eval_router, prefix="/api/prompt-evaluations", tags=["prompt-eval"])
app.include_router(prompt_chain_router, prefix="/api/prompt-chains", tags=["prompt-chain"])

# M3: MCP Server — API Key 认证中间件 + /mcp 端点挂载（Streamable HTTP）
app.add_middleware(MCPAuthMiddleware, api_key=settings.MCP_API_KEY)
app.mount("/mcp", mcp_app)

@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
