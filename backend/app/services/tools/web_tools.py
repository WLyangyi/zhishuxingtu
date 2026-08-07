import json

from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """搜索互联网(占位实现,M3 接真实 Tavily/duckduckgo)。"""
    return json.dumps(
        {"error": "web_search 尚未接入真实服务(M3 实现)", "query": query},
        ensure_ascii=False,
    )
