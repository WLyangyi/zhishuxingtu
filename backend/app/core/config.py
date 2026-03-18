from pydantic_settings import BaseSettings

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
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
