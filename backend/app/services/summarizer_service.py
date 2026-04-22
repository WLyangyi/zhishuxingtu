import json
import re
from typing import Optional, List, Dict, Any
from openai import OpenAI
from app.core.config import settings


SUMMARY_PROMPT_PDF = """你是一个专业的学术论文和技术文档分析助手。请根据以下从PDF文档中提取的内容，生成结构化摘要。

【标题生成规范】
- 生成 5-15 字的中文标题
- 标题应简洁明了，突出核心主题
- 避免使用"关于...的研究"、"...的分析"等通用开头
- 示例：「Transformer核心解读」而非「关于Transformer论文的分析」

【摘要生成规范】
- 长度：200-500 字
- 结构要求：
  1. 一句话概括核心主题（50字以内）
  2. 背景/问题：说明研究的背景或要解决的问题
  3. 核心内容：详细说明主要观点、方法、发现、实验结果
  4. 价值/应用：研究的意义或实际应用场景
- 语言风格：正式书面语，客观陈述，避免主观评价
- 重点说明：创新点、实验数据、学术贡献

【关键要点生成规范】
- 生成 3-8 个关键要点
- 每个要点 20-100 字
- 要点类型分布：
  - 概念类（约30%）：定义、原理、机制
  - 方法类（约30%）：技术、算法、流程、步骤
  - 结论类（约25%）：发现、结果、观点、规律
  - 应用类（约15%）：场景、案例、实践、注意事项
- 每个要点使用「•」开头，言简意赅，层次分明

【标签生成规范】
- 生成 3-8 个标签
- 标签类型：
  - 主题标签：内容所属的领域/学科
  - 技术标签：涉及的技术、工具、框架
  - 场景标签：适用场景、使用条件
  - 格式标签：内容形式（论文/文档等）
- 标签格式：2-6 字的中文词或英文词

【内容类型判断】
- 判断内容类型：论文、教程、技术文档、报告、书籍、其他

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
```json
{{
  "title": "5-15字的标题",
  "summary": "200-500字的摘要",
  "key_points": ["• 要点1：概念/原理说明...", "• 要点2：方法/技术说明...", "• 要点3：结论/发现说明..."],
  "tags": ["标签1", "标签2", "标签3"],
  "content_type": "论文|教程|技术文档|报告|书籍|其他",
  "language_detected": "zh|en|multi"
}}
```

提取的内容如下：
---
{content}
---"""

SUMMARY_PROMPT_WEB = """你是一个专业的网络内容分析助手。请根据以下从网页中提取的内容，生成结构化摘要。

【标题生成规范】
- 生成 5-15 字的中文标题
- 标题应简洁明了，突出核心主题
- 避免使用"关于...的研究"、"...的分析"等通用开头

【摘要生成规范】
- 长度：200-500 字
- 结构要求：
  1. 一句话概括核心主题（50字以内）
  2. 背景/问题：说明内容的背景或要解决的问题
  3. 核心内容：详细说明主要观点、实用信息、核心内容
  4. 价值/应用：内容的意义或实际应用场景
- 语言风格：正式书面语，客观陈述
- 重点说明：观点陈述、实用信息、时效性

【关键要点生成规范】
- 生成 3-8 个关键要点
- 每个要点 20-100 字
- 要点类型分布：
  - 概念类（约30%）：定义、原理、机制
  - 方法类（约30%）：技术、算法、流程、步骤
  - 结论类（约25%）：发现、结果、观点、规律
  - 应用类（约15%）：场景、案例、实践、注意事项
- 每个要点使用「•」开头，言简意赅

【标签生成规范】
- 生成 3-8 个标签
- 标签类型：主题标签、技术标签、场景标签、格式标签
- 标签格式：2-6 字的中文词或英文词

【内容类型判断】
- 判断内容类型：博客、新闻、教程、文档、其他

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
```json
{{
  "title": "5-15字的标题",
  "summary": "200-500字的摘要",
  "key_points": ["• 要点1...", "• 要点2...", "• 要点3..."],
  "tags": ["标签1", "标签2", "标签3"],
  "content_type": "博客|新闻|教程|文档|其他",
  "language_detected": "zh|en|multi"
}}
```

提取的内容如下：
---
{content}
---"""

SUMMARY_PROMPT_VIDEO = """你是一个专业的视频内容分析助手。请根据以下从视频中提取的字幕/转录内容，生成结构化摘要。

【标题生成规范】
- 生成 5-15 字的中文标题
- 标题应简洁明了，突出核心主题
- 避免使用"关于...的研究"、"...的分析"等通用开头

【摘要生成规范】
- 长度：200-500 字
- 结构要求：
  1. 一句话概括核心主题（50字以内）
  2. 背景/问题：说明视频的背景或讨论的话题
  3. 核心内容：详细说明主要讨论点、干货内容、关键信息
  4. 价值/应用：视频的意义或实际应用场景
- 语言风格：正式书面语，客观陈述
- 重点说明：核心话题、讨论要点、干货内容、可操作性建议

【关键要点生成规范】
- 生成 3-8 个关键要点
- 每个要点 20-100 字
- 要点类型分布：
  - 概念类（约30%）：定义、原理、机制
  - 方法类（约30%）：技术、算法、流程、步骤
  - 结论类（约25%）：发现、结果、观点、规律
  - 应用类（约15%）：场景、案例、实践、注意事项
- 每个要点使用「•」开头，言简意赅
- 注意：口语化内容需要提炼为书面表达

【标签生成规范】
- 生成 3-8 个标签
- 标签类型：主题标签、技术标签、场景标签、格式标签
- 标签格式：2-6 字的中文词或英文词

【内容类型判断】
- 判断内容类型：教程、演讲、访谈、纪录片、其他

请严格按照以下 JSON 格式返回，不要添加任何其他内容：
```json
{{
  "title": "5-15字的标题",
  "summary": "200-500字的摘要",
  "key_points": ["• 要点1...", "• 要点2...", "• 要点3..."],
  "tags": ["标签1", "标签2", "标签3"],
  "content_type": "教程|演讲|访谈|纪录片|其他",
  "language_detected": "zh|en|multi"
}}
```

提取的内容如下：
---
{content}
---"""

LONG_CONTENT_PROMPT = """你是一个专业的文档摘要助手。以下内容较长，已分段处理。请综合所有内容生成结构化摘要。

【标题生成规范】
- 生成 5-15 字的中文标题
- 标题应简洁明了，突出核心主题
- 避免使用"关于...的研究"等通用开头

【摘要生成规范】
- 长度：200-500 字
- 结构：核心主题 → 背景/问题 → 核心内容 → 价值/应用

【关键要点生成规范】
- 生成 3-8 个关键要点，每个 20-100 字
- 要点类型：概念类30%、方法类30%、结论类25%、应用类15%
- 使用「•」开头

【标签生成规范】
- 生成 3-8 个标签

请严格按照以下 JSON 格式返回：
```json
{{
  "title": "5-15字的标题",
  "summary": "200-500字的摘要",
  "key_points": ["• 要点1...", "• 要点2...", "• 要点3..."],
  "tags": ["标签1", "标签2", "标签3"],
  "content_type": "论文|教程|博客|视频|文档|其他",
  "language_detected": "zh|en|multi"
}}
```

分段内容如下：
---
{content}
---"""

CATEGORY_SUGGEST_PROMPT = """你是一个知识分类助手。根据以下文档信息，从给定的文件夹列表中推荐最合适的存储位置。

【待分析内容】
- 标题：{title}
- 摘要：{summary}
- 关键词：{keywords}
- 标签：{tags}
- 内容类型：{content_type}
- 来源：{source_type}

【可用文件夹列表】
{folders}

【分类决策因素】
1. 内容主题分析（摘要、关键词、标签）
2. 内容类型判断（论文/教程/新闻/笔记等）
3. 来源判断（PDF/网页/视频）
4. 用户已有文件夹结构

请返回最推荐的文件夹和备选方案，严格按照以下 JSON 格式返回：
```json
{{
  "recommended_folder_id": "推荐的文件夹ID",
  "recommended_folder_path": "推荐的文件夹路径",
  "confidence_score": 0.85,
  "reasoning": "推荐理由（不超过100字）",
  "alternatives": [
    {{
      "folder_id": "备选文件夹ID",
      "folder_path": "备选文件夹路径",
      "confidence_score": 0.45,
      "reasoning": "备选理由"
    }}
  ]
}}
```

【置信度评分标准】
- 0.9-1.0：高度匹配，内容主题与分类高度一致
- 0.7-0.9：良好匹配，内容与分类相关
- 0.5-0.7：一般匹配，需要用户确认
- < 0.5：低匹配，建议用户手动选择"""


class SummarizerService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
        self.max_content_length = 30000
        self.chunk_size = 15000

    def summarize(self, content: str, source_type: str = "文档") -> dict:
        if len(content) > self.max_content_length:
            return self._summarize_long_content(content, source_type)
        return self._summarize_content(content, source_type)

    def _get_prompt_by_source_type(self, source_type: str) -> str:
        source_type_lower = source_type.lower()
        if "pdf" in source_type_lower or "论文" in source_type_lower:
            return SUMMARY_PROMPT_PDF
        elif "网页" in source_type_lower or "web" in source_type_lower or "url" in source_type_lower:
            return SUMMARY_PROMPT_WEB
        elif "视频" in source_type_lower or "video" in source_type_lower:
            return SUMMARY_PROMPT_VIDEO
        else:
            return SUMMARY_PROMPT_PDF

    def _summarize_content(self, content: str, source_type: str) -> dict:
        prompt_template = self._get_prompt_by_source_type(source_type)
        prompt = prompt_template.format(content=content)
        return self._call_llm(prompt)

    def _summarize_long_content(self, content: str, source_type: str) -> dict:
        chunks = []
        for i in range(0, len(content), self.chunk_size):
            chunks.append(content[i:i + self.chunk_size])

        if len(chunks) <= 3:
            combined = "\n\n--- 分段 ---\n\n".join(chunks)
            prompt = LONG_CONTENT_PROMPT.format(content=combined)
            return self._call_llm(prompt)

        chunk_summaries = []
        for i, chunk in enumerate(chunks[:5]):
            prompt = f"请简要概括以下第{i+1}段内容（100字以内）：\n\n{chunk[:8000]}"
            try:
                result = self._call_llm(prompt, expect_json=False)
                chunk_summaries.append(result.get("text", ""))
            except Exception:
                continue

        combined_summary = "\n\n".join(chunk_summaries)
        prompt = LONG_CONTENT_PROMPT.format(content=combined_summary)
        return self._call_llm(prompt)

    def suggest_category(
        self, 
        summary: str, 
        folders: List[dict],
        title: str = "",
        keywords: List[str] = None,
        tags: List[str] = None,
        content_type: str = "",
        source_type: str = ""
    ) -> Optional[dict]:
        if not folders:
            return None

        folder_list = "\n".join([
            f"- ID: {f['id']}, 名称: {f['name']}, 路径: {f.get('path', f['name'])}"
            for f in folders
        ])

        keywords_str = ", ".join(keywords) if keywords else "无"
        tags_str = ", ".join(tags) if tags else "无"

        prompt = CATEGORY_SUGGEST_PROMPT.format(
            title=title or "未知标题",
            summary=summary,
            keywords=keywords_str,
            tags=tags_str,
            content_type=content_type or "未知",
            source_type=source_type or "未知",
            folders=folder_list
        )
        
        try:
            result = self._call_llm(prompt)
            if result:
                result["recommended_folder_id"] = self._extract_folder_id(
                    result.get("recommended_folder_id", ""), 
                    folders
                )
                for alt in result.get("alternatives", []):
                    alt["folder_id"] = self._extract_folder_id(
                        alt.get("folder_id", ""), 
                        folders
                    )
            return result
        except Exception:
            return None

    def _extract_folder_id(self, folder_id: str, folders: List[dict]) -> str:
        if not folder_id:
            return ""
        
        for f in folders:
            if str(f["id"]) == str(folder_id) or f["id"] == folder_id:
                return str(f["id"])
        
        try:
            for f in folders:
                if folder_id in str(f["id"]) or str(f["id"]) in folder_id:
                    return str(f["id"])
        except Exception:
            pass
        
        return folder_id

    def regenerate_field(
        self, 
        content: str, 
        field: str, 
        source_type: str = "文档",
        current_result: dict = None
    ) -> dict:
        if field == "title":
            return self._regenerate_title(content, source_type)
        elif field == "summary":
            return self._regenerate_summary(content, source_type)
        elif field == "key_points":
            return self._regenerate_key_points(content, source_type)
        elif field == "tags":
            return self._regenerate_tags(content, source_type)
        else:
            return self.summarize(content, source_type)

    def _regenerate_title(self, content: str, source_type: str) -> dict:
        prompt = f"""请根据以下内容生成一个简洁准确的标题。

要求：
- 5-15 个中文字
- 突出核心主题
- 避免使用"关于...的研究"等通用开头

内容摘要：
{content[:2000]}

请只返回标题文本，不要添加任何其他内容。"""
        
        try:
            result = self._call_llm(prompt, expect_json=False)
            return {"title": result.get("text", "").strip()}
        except Exception:
            return {"title": "导入文档"}

    def _regenerate_summary(self, content: str, source_type: str) -> dict:
        prompt = f"""请根据以下内容生成一个结构化摘要。

要求：
- 长度：200-500 字
- 结构：核心主题 → 背景/问题 → 核心内容 → 价值/应用
- 语言风格：正式书面语，客观陈述

内容：
{content[:5000]}

请只返回摘要文本，不要添加任何其他内容。"""
        
        try:
            result = self._call_llm(prompt, expect_json=False)
            return {"summary": result.get("text", "").strip()}
        except Exception:
            return {"summary": "无法生成摘要"}

    def _regenerate_key_points(self, content: str, source_type: str) -> dict:
        prompt = f"""请根据以下内容生成关键要点。

要求：
- 生成 3-8 个关键要点
- 每个要点 20-100 字
- 要点类型：概念类30%、方法类30%、结论类25%、应用类15%
- 使用「•」开头

内容：
{content[:5000]}

请严格按照以下 JSON 格式返回：
```json
{{
  "key_points": ["• 要点1...", "• 要点2...", "• 要点3..."]
}}
```"""
        
        try:
            result = self._call_llm(prompt)
            return {"key_points": result.get("key_points", [])}
        except Exception:
            return {"key_points": ["• 内容解析完成"]}

    def _regenerate_tags(self, content: str, source_type: str) -> dict:
        prompt = f"""请根据以下内容生成标签。

要求：
- 生成 3-8 个标签
- 标签类型：主题标签、技术标签、场景标签、格式标签
- 标签格式：2-6 字的中文词或英文词

内容摘要：
{content[:2000]}

请严格按照以下 JSON 格式返回：
```json
{{
  "tags": ["标签1", "标签2", "标签3"]
}}
```"""
        
        try:
            result = self._call_llm(prompt)
            return {"tags": result.get("tags", [])}
        except Exception:
            return {"tags": ["导入"]}

    def _call_llm(self, prompt: str, expect_json: bool = True) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文档分析助手，总是返回有效的JSON格式。注意：标题必须是5-15字，摘要必须是200-500字，关键要点每个20-100字。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
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

            if "title" in result:
                result["title"] = self._validate_title(result.get("title", ""))
            if "summary" in result:
                result["summary"] = self._validate_summary(result.get("summary", ""))
            if "key_points" in result:
                result["key_points"] = self._validate_key_points(result.get("key_points", []))
            if "tags" in result:
                result["tags"] = self._validate_tags(result.get("tags", []))

            return result

        except json.JSONDecodeError:
            return {
                "title": self._validate_title("导入文档"),
                "summary": self._validate_summary(text[:500] if text else "无法生成摘要"),
                "key_points": ["• 内容解析完成"],
                "tags": ["导入"],
                "content_type": "其他",
                "language_detected": "zh"
            }
        except Exception as e:
            raise RuntimeError(f"AI 摘要生成失败: {str(e)}")

    def _validate_title(self, title: str) -> str:
        title = title.strip()
        title = re.sub(r'^["「『]|["」』]$', '', title)
        if len(title) > 20:
            title = title[:20]
        if len(title) < 3:
            title = "导入文档"
        return title

    def _validate_summary(self, summary: str) -> str:
        summary = summary.strip()
        if len(summary) < 100:
            pass
        if len(summary) > 600:
            summary = summary[:600] + "..."
        return summary

    def _validate_key_points(self, key_points: List[str]) -> List[str]:
        validated = []
        for point in key_points[:8]:
            point = point.strip()
            if not point.startswith("•"):
                point = "• " + point
            if len(point) > 120:
                point = point[:117] + "..."
            if len(point) > 5:
                validated.append(point)
        if not validated:
            validated = ["• 内容解析完成"]
        return validated

    def _validate_tags(self, tags: List[str]) -> List[str]:
        validated = []
        for tag in tags[:8]:
            tag = tag.strip()
            tag = re.sub(r'[,，、\s]+', '', tag)
            if 2 <= len(tag) <= 10:
                validated.append(tag)
        if not validated:
            validated = ["导入"]
        return validated


_summarizer_service_instance = None


def get_summarizer_service() -> SummarizerService:
    global _summarizer_service_instance
    if _summarizer_service_instance is None:
        _summarizer_service_instance = SummarizerService()
    return _summarizer_service_instance
