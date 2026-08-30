# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

知枢星图 - 个人知识库系统，支持双向链接、知识图谱、AI 智能问答、RAG 检索增强生成。

## 开发命令

### 后端 (Python 3.11+)

```bash
cd backend

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python -m uvicorn app.main:app --reload --port 8000

# 运行测试
pytest backend/tests/
```

### 前端 (Node.js 18+)

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.4 + TypeScript + Pinia + Naive UI + Tailwind CSS + D3 |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + FAISS + LangChain + LangGraph |
| AI | DeepSeek agent（LangGraph 意图路由 + ReAct + 三查）+ qwen Embedding/裁判 + RAG + SSE |

## 架构概览

```
知枢星图/
├── frontend/src/
│   ├── api/             # API 客户端 (axios)
│   ├── components/      # Vue 组件 (sidebar, layout, common)
│   ├── views/           # 页面视图 (NoteEditor, GraphView, AIAssistant 等)
│   ├── stores/          # Pinia 状态管理
│   ├── router/          # 路由配置
│   └── types/           # TypeScript 类型定义
│
└── backend/app/
    ├── api/routes/      # API 路由 (notes, folders, tags, search, graph, skills, prompts)
    ├── core/            # 核心配置 (config, security)
    ├── db/              # 数据库会话和基类
    ├── models/          # SQLAlchemy 数据模型
    ├── schemas/         # Pydantic 请求/响应模型
    └── services/        # 业务逻辑 (agent/, llm/, tools/, observability/, RAG, embedding, vector store)
```

## 核心模块

- **笔记管理**: `backend/app/api/routes/notes.py` - 支持双向链接 (`[[标题]]` 语法)
- **知识图谱**: `backend/app/api/routes/graph.py` - 全局/局部图谱可视化
- **Agentic RAG**: `backend/app/services/agent/` + `llm/` + `tools/` - 入口意图识别四分类路由（`intent_classify`：knowledge / direct_answer / web_search / note_write）+ LangGraph ReAct 循环 + 三查强制节点（grade_documents / hallucination_check / answer_quality）+ 7 个工具（DeepSeek provider，含 web_search / create_note HITL）；`direct_answer` 短路直答省 token，`execute_tool` 对重复检索/永久不可用工具熔断防死循环
- **MCP Server**: `backend/app/services/mcp_server.py` - 知识库 MCP 化（`/mcp` 端点，API Key 认证，与 agent 共享工具层）
- **AI 问答**: `backend/app/services/rag_chain.py` - RAG 检索 + 流式输出（agent 降级 fallback）
- **向量检索**: `backend/app/services/vector_store.py` - FAISS 向量索引 + 混合检索
- **评估体系**: `backend/eval/` + `services/llm/judge_metrics.py` - 50 条 eval set + qwen3.7-max-2026-06-08 独立裁判（`run_eval.py` 跑新旧对比，报告在 `eval/reports/`）
- **Prompt 系统**: PromptLab + Skill Chain + Few-Shot 学习

## 数据模型

核心实体关系：
- User → Notes (一对多)
- Folder → Notes (一对多，支持 4 层嵌套)
- Category → Folders (一对多，三大分类：个人/工作/素材)
- Note ↔ Tag (多对多)
- Note ↔ Note (双向链接，通过 `linked_note_ids` 字段)
- agent_sessions / agent_tool_calls - Agent 会话与工具调用审计（M1）
- eval_sets / eval_runs - 评测题库与成绩单（M2）
- user_preferences - 用户长期偏好，跨会话记忆（M4）

## 环境变量

后端需要配置 `backend/.env` 文件（参考 `.env.example`）：
- `DASHSCOPE_API_KEY` - 阿里云 DashScope API（向量化 + 裁判）
- `JWT_SECRET_KEY` - JWT 认证密钥
- `DATABASE_URL` - SQLite 数据库路径
- `FAISS_INDEX_PATH` - 向量索引路径
- `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL=deepseek-v4-flash` / `DEEPSEEK_THINKING=disabled` - Agent 推理（M1，P2 必须关思考）
- `QWEN_EMBEDDING_MODEL=qwen3.7-text-embedding` - Embedding（M0）
- `QWEN_JUDGE_MODEL=qwen3.7-plus-2026-05-26` - 评估裁判（qwen3.7-max/plus 免费额度连环耗尽 403、qwen3.7-flash 拼写漂移不可用→P22 容错已加；勿切回耗尽的模型）
- `AGENT_MULTI_AGENT=false` - M7 A′ 多 Agent 图开关（true=编排器路由 4 子 Agent 的平铺图，false=单 Agent 图回退位）
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` - 可观测（M2，fail-silent；trace 上报遗留，需干净 `.venv-clean`）
- `MCP_API_KEY` - MCP Server `/mcp` 认证（M3，为空则 fail-closed 拒绝所有请求）
- `TAVILY_API_KEY` - web_search 联网搜索（M3，为空则工具优雅降级）

## API 路由前缀

所有 API 路由均以 `/api` 为前缀，主要端点：
- `/api/notes` - 笔记 CRUD
- `/api/folders` - 文件夹管理
- `/api/tags` - 标签管理
- `/api/search` - 搜索 + AI 问答
- `/api/graph` - 知识图谱
- `/api/skills` - Skill 执行引擎
- `/api/prompts` - Prompt 管理
- `/api/agent/chat/stream` - Agent ReAct 问答（SSE 流式）
- `/api/agent/sessions` - Agent 会话管理

## 深入文档

- [Code Wiki](docs/CODE_WIKI.md) — 代码架构全览（模块职责、核心类/函数、API 路由）
- [启动文档](docs/启动文档.md) — Windows/Anaconda 环境启动指南与故障排查
- [产品需求文档 (PRD)](docs/superpowers/specs/prd.md)
- [技术架构](docs/superpowers/specs/技术架构.md)
- [开发实施文档](docs/superpowers/specs/开发实施文档.md)
- [Agentic RAG 升级笔记](docs/agentic-rag-upgrade/升级笔记.md) — Agentic RAG 升级的决策/踩坑/进展（持续维护）
- [Agentic RAG 实施计划](docs/agentic-rag-upgrade/实施计划.md) — M0-M6 执行步骤清单（M0/M1/M2 已细化，M6 意图识别）
- [Agentic RAG 待做清单](docs/agentic-rag-upgrade/待做清单.md) — M0-M5 收尾遗留与新发现缺陷（2026-08-28 盘点）
