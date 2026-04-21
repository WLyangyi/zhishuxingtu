import json
from typing import Optional, List
from openai import OpenAI
from app.core.config import settings


SUMMARY_PROMPT = """你是一个专业的文档摘要助手。请根据以下从{source_type}中提取的内容，生成结构化摘要。

要求：
1. 标题：简洁准确的文档标题（不超过50字）
2. 摘要：100-200字的内容摘要，概括核心内容
3. 要点：3-5个关键要点，每个要点不超过30字
4. 标签：3-5个相关标签，用于分类和检索

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
```json
{{
  "title": "文档标题",
  "summary": "内容摘要",
  "key_points": ["要点1", "要点2", "要点3"],
  "tags": ["标签1", "标签2", "标签3"]
}}
```

提取的内容如下：
---
{content}
---"""

LONG_CONTENT_PROMPT = """你是一个专业的文档摘要助手。以下内容较长，已分段处理。请综合所有内容生成结构化摘要。

要求：
1. 标题：简洁准确的文档标题（不超过50字）
2. 摘要：100-200字的内容摘要，概括核心内容
3. 要点：3-5个关键要点，每个要点不超过30字
4. 标签：3-5个相关标签，用于分类和检索

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
```json
{{
  "title": "文档标题",
  "summary": "内容摘要",
  "key_points": ["要点1", "要点2", "要点3"],
  "tags": ["标签1", "标签2", "标签3"]
}}
```

分段内容如下：
---
{content}
---"""

CATEGORY_SUGGEST_PROMPT = """你是一个知识分类助手。根据以下文档摘要，从给定的文件夹列表中推荐最合适的存储位置。

文档摘要：{summary}

可用文件夹：
{folders}

请返回最推荐的文件夹ID和理由，严格按照以下 JSON 格式返回：
```json
{{
  "folder_id": "推荐的文件夹ID",
  "reason": "推荐理由（不超过50字）"
}}
```"""


class SummarizerService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL

    def summarize(self, content: str, source_type: str = "文档") -> dict:
        if len(content) > 30000:
            return self._summarize_long_content(content, source_type)
        return self._summarize_content(content, source_type)

    def _summarize_content(self, content: str, source_type: str) -> dict:
        prompt = SUMMARY_PROMPT.format(source_type=source_type, content=content)
        return self._call_llm(prompt)

    def _summarize_long_content(self, content: str, source_type: str) -> dict:
        chunk_size = 15000
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i:i + chunk_size])

        if len(chunks) <= 3:
            combined = "\n\n--- 分段 ---\n\n".join(chunks)
            prompt = LONG_CONTENT_PROMPT.format(content=combined)
            return self._call_llm(prompt)

        chunk_summaries = []
        for i, chunk in enumerate(chunks[:5]):
            prompt = f"请简要概括以下第{i+1}段内容（100字以内）：\n\n{chunk[:8000]}"
            try:
                result = self._call_llm(prompt, expect_json=False)
                chunk_summaries.append(result)
            except Exception:
                continue

        combined_summary = "\n\n".join(chunk_summaries)
        prompt = LONG_CONTENT_PROMPT.format(content=combined_summary)
        return self._call_llm(prompt)

    def suggest_category(self, summary: str, folders: List[dict]) -> Optional[dict]:
        if not folders:
            return None

        folder_list = "\n".join([
            f"- ID: {f['id']}, 名称: {f['name']}"
            for f in folders
        ])

        prompt = CATEGORY_SUGGEST_PROMPT.format(summary=summary, folders=folder_list)
        try:
            return self._call_llm(prompt)
        except Exception:
            return None

    def _call_llm(self, prompt: str, expect_json: bool = True) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文档分析助手，总是返回有效的JSON格式。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )

            text = response.choices[0].message.content.strip()

            if not expect_json:
                return {"text": text}

            json_str = text
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            result = json.loads(json_str)

            if "title" not in result or "summary" not in result:
                raise ValueError("LLM 返回格式不正确")

            return result

        except json.JSONDecodeError:
            return {
                "title": "导入文档",
                "summary": text[:200] if text else "无法生成摘要",
                "key_points": ["内容解析完成"],
                "tags": ["导入"]
            }
        except Exception as e:
            raise RuntimeError(f"AI 摘要生成失败: {str(e)}")


_summarizer_service_instance = None


def get_summarizer_service() -> SummarizerService:
    global _summarizer_service_instance
    if _summarizer_service_instance is None:
        _summarizer_service_instance = SummarizerService()
    return _summarizer_service_instance
