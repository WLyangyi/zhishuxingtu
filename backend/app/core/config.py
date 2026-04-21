from pydantic_settings import BaseSettings
import os


def get_faiss_path():
    custom_path = os.environ.get('FAISS_INDEX_PATH')
    if custom_path:
        return custom_path
    
    for base_path in ['C:/temp', 'D:/temp', 'E:/temp']:
        try:
            os.makedirs(base_path, exist_ok=True)
            if os.access(base_path, os.W_OK):
                return os.path.join(base_path, 'zhishuxingtu_faiss')
        except:
            continue
    
    return 'C:/temp/zhishuxingtu_faiss'


class Settings(BaseSettings):
    APP_NAME: str = "知枢星图"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key"
    
    DATABASE_URL: str = "sqlite:///./data/knowledge.db"
    
    JWT_SECRET_KEY: str = "your-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 7
    
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "qwen-turbo"
    
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"
    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    HF_MIRROR_URL: str = "https://hf-mirror.com"
    HF_CACHE_DIR: str = "C:/temp/huggingface_cache"
    
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

    USE_VECTOR_MEMORY: bool = True
    CHAT_MEMORY_INDEX_PATH: str = "C:/temp/zhishuxingtu_chat_memory"
    CHAT_MEMORY_TOP_K: int = 5
    CHAT_MEMORY_MIN_SCORE: float = 0.3

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

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        case_sensitive = True

settings = Settings()
