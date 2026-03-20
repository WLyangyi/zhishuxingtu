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

    USE_VECTOR_MEMORY: bool = True
    CHAT_MEMORY_INDEX_PATH: str = "C:/temp/zhishuxingtu_chat_memory"
    CHAT_MEMORY_TOP_K: int = 5
    CHAT_MEMORY_MIN_SCORE: float = 0.3

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
