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

    # M2: 评估独立裁判（与推理模型不同源）。JUDGE_PROVIDER=glm / qwen
    JUDGE_PROVIDER: str = "glm"
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    GLM_JUDGE_MODEL: str = "glm-5.3-flash"
    QWEN_JUDGE_MODEL: str = "qwen3.7-max-2026-06-08"      # 仅 JUDGE_PROVIDER=qwen 时使用

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
    # Phase 3 消融开关(默认保持生产行为;仅 eval/ablation_runner.py 用环境变量覆盖)
    USE_THREE_CHECK: bool = True   # false=跳过 grade_documents / hallucination_check / answer_quality 三查
    FORCE_INTENT: str = ""         # 非空=意图路由短路为指定意图(如 knowledge),用于消融"去意图路由"

    # Phase 4 可靠性:单次工具调用硬超时(秒)。工具内部各自有 HTTP 超时,这里防的是
    # embedding / DB / 未来接入的第三方工具卡死,把整条 SSE 链路的单轮拖到不可控。
    AGENT_TOOL_TIMEOUT_SECONDS: float = 30.0
    # 同一工具本轮失败(含超时)达到该次数即熔断,后续调用直接短路,不再真调、不再烧 token
    AGENT_MAX_TOOL_FAILURES: int = 2
    # Phase 4:单条工具结果超过该字符数就 offload——全文落库,消息里只留压缩预览。
    # 1000 字以内的结果(常规检索 top_k=5 约 1.5k)几乎不受影响,避免小结果也走落库。
    AGENT_ARTIFACT_THRESHOLD_CHARS: int = 4000
    # Phase 4 可靠性:LLM 指数退避(只重试瞬时错误:超时/连接/限流/5xx)
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_ATTEMPTS: int = 3
    LLM_RETRY_BASE_DELAY: float = 1.0
    # Phase 4:每会话跨轮累计预算。超出后下一次请求直接硬停并返回降级答复,不再调用 LLM。
    AGENT_SESSION_TOKEN_BUDGET: int = 200000
    AGENT_SESSION_COST_BUDGET_CNY: float = 1.0
    # 成本换算口径(与 eval 的 COST_PER_1K_TOKENS_CNY 保持一致,便于横向对比)
    AGENT_COST_PER_1K_TOKENS_CNY: float = 0.002

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

    # Phase 5: GraphRAG-lite(双向链接 1 跳邻居扩展 + RRF)
    GRAPH_RAG_ENABLED: bool = True
    GRAPH_RAG_NEIGHBOR_LIMIT: int = 5      # 最多补充多少篇邻居笔记
    GRAPH_RAG_NEIGHBOR_WEIGHT: float = 0.5 # 邻居在 RRF 中的权重(<1 保证不挤掉精确命中)

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
    # LANGFUSE_ENABLED=false 供离线批跑显式关闭上报：不能靠清空 key 来关，
    # Windows 下把环境变量设成空串等价于删除变量，最终仍会回退读 .env 里的真 key。
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_TIMEOUT: int = 5

    # M2: 评估配置
    EVAL_SET_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "eval_set_v1.json")
    EVAL_REPORT_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "reports")

    # M3: MCP Server 认证（Authorization: Bearer <MCP_API_KEY>；为空则 /mcp 拒绝所有请求）
    MCP_API_KEY: str = ""

    # Phase 4: MCP 权限分级。默认只暴露只读工具；写工具需显式开启并绑定写入用户。
    # MCP_DRY_RUN 默认 True：即便开了写权限，首次也只演练不落库，确认后再关。
    MCP_ENABLE_WRITE: bool = False
    MCP_DRY_RUN: bool = True
    # 通过 MCP 写笔记时归属的用户 id（users.id）；为空则拒发写权限（fail-closed）
    MCP_WRITE_USER_ID: str = ""

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
