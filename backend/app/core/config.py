from pydantic_settings import BaseSettings
import os
import tempfile


def get_faiss_path():
    custom_path = os.environ.get('FAISS_INDEX_PATH')
    if custom_path:
        return custom_path
    
    base_path = tempfile.gettempdir()
    try:
        os.makedirs(base_path, exist_ok=True)
        if os.access(base_path, os.W_OK):
            return os.path.join(base_path, 'zhishuxingtu_faiss')
    except Exception:
        pass
    
    return os.path.join(tempfile.gettempdir(), 'zhishuxingtu_faiss')


class Settings(BaseSettings):
    APP_NAME: str = "知枢星图"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    
    DATABASE_URL: str = "sqlite:///./data/knowledge.db"
    
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 7
    
    CORS_ORIGINS: list = ["http://localhost:5173"]
    
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "qwen-turbo"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_THINKING: str = "disabled"

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"
    QWEN_EMBEDDING_MODEL: str = "qwen3.7-text-embedding"
    QWEN_JUDGE_MODEL: str = "qwen3.7-max-2026-06-08"      # M2: 评估独立裁判（与推理模型不同源）

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    HF_MIRROR_URL: str = "https://hf-mirror.com"
    HF_CACHE_DIR: str = os.path.join(tempfile.gettempdir(), "huggingface_cache")
    
    FAISS_INDEX_PATH: str = get_faiss_path()

    USE_LANGCHAIN_EMBEDDINGS: bool = False
    USE_LANGCHAIN_VECTORSTORE: bool = False
    USE_LANGCHAIN_PROMPT: bool = False
    USE_LANGCHAIN_RAG: bool = False
    USE_LANGCHAIN_CHAT: bool = False
    USE_LANGCHAIN_SKILL: bool = False

    # 统一递归分块配置 (V3.6)
    MAX_CHUNK_SIZE: int = 800           # 每块最大字符数
    OVERLAP_RATIO: float = 0.5         # 相邻块重叠比例（50%）
    MIN_CHUNK_SIZE: int = 50           # 每块最小字符数
    CHUNK_BY_DIVIDER: bool = True      # 是否按 --- 分割
    CHUNK_BY_HEADING: bool = True      # 是否按标题分割
    CHUNK_BY_PARAGRAPH: bool = True    # 是否按段落分割
    CHUNK_BY_SENTENCE: bool = True     # 是否按句子分割（保底）

    # 旧 FAISS 对话记忆已由 LangGraph checkpoint + store 取代，仅保留开关兼容旧 .env。
    USE_VECTOR_MEMORY: bool = False
    CHAT_MEMORY_INDEX_PATH: str = os.path.join(tempfile.gettempdir(), "zhishuxingtu_chat_memory")
    CHAT_MEMORY_TOP_K: int = 5
    CHAT_MEMORY_MIN_SCORE: float = 0.3

    # M4: Agent 短期 checkpoint / 长期 store / 上下文控制
    AGENT_MAX_ITERATIONS: int = 8
    AGENT_TOKEN_BUDGET: int = 10000
    AGENT_MAX_HISTORY_MESSAGES: int = 24
    AGENT_CHECKPOINT_DB: str = os.path.join("data", "langgraph_checkpoints.db")
    # M7: A′ 多 Agent 图开关(false=单 Agent 图回退位,双图共存支持一键回滚与 eval 同进程对比)
    AGENT_MULTI_AGENT: bool = False

    USE_RERANKER: bool = True
    RERANKER_TOP_K: int = 5
    RERANKER_CANDIDATES: int = 15

    # BM25 混合检索配置 (V3.7)
    USE_HYBRID_SEARCH: bool = True          # 是否启用混合检索
    VECTOR_WEIGHT: float = 0.6              # 向量检索权重
    BM25_WEIGHT: float = 0.4                # BM25 权重
    RRF_K: int = 60                        # RRF 平滑参数
    HYBRID_TOP_K: int = 10                 # 混合检索返回数量
    BM25_TOP_K: int = 15                   # BM25 候选集大小

    # 智能导入配置 (V4)
    IMPORT_MAX_FILE_SIZE: int = 209715200   # 200MB
    IMPORT_MAX_CHARS: int = 50000           # 最大处理字符数
    IMPORT_TIMEOUT: int = 300               # 处理超时（秒）
    IMPORT_TEMP_DIR: str = "./temp/imports" # 临时文件目录

    # Whisper 语音转文字配置
    WHISPER_MODEL: str = "base"             # tiny/base/small/medium/large
    WHISPER_DEVICE: str = "cpu"             # cpu/cuda

    # AI 搜索配置
    AI_MAX_TOKENS: int = 1000
    AI_TEMPERATURE: float = 0.7

    # M2: Langfuse 可观测（fail-silent，key 缺失不影响主流程）
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_TIMEOUT: int = 5

    # M2: 评估配置
    EVAL_SET_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "eval_set_v1.json")
    EVAL_REPORT_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "reports")

    # M3: MCP Server 认证（Authorization: Bearer <MCP_API_KEY>；为空则 /mcp 拒绝所有请求）
    MCP_API_KEY: str = ""

    # M3-2: web_search 联网搜索（Tavily；key 为空则工具优雅降级返回未启用提示）
    TAVILY_API_KEY: str = ""
    TAVILY_MAX_RESULTS: int = 5     # 每次搜索返回条数
    TAVILY_TIMEOUT: int = 15        # Tavily API 超时（秒）

    # B站登录凭证配置（可选，用于获取官方字幕）
    BILIBILI_SESSDATA: str = ""
    BILIBILI_BILI_JCT: str = ""
    BILIBILI_BUVID3: str = ""
    BILIBILI_DEDEUSERID: str = ""

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        case_sensitive = True

settings = Settings()
