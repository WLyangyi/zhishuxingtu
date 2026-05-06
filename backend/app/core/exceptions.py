from app.core.config import settings

def sanitize_error(e: Exception, context: str = "操作") -> str:
    if settings.DEBUG:
        return f"{context}失败：{str(e)}"
    return f"{context}失败，请稍后重试"
