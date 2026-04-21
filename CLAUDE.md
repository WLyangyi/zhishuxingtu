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
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + FAISS + LangChain |
| AI | 通义千问 Embedding + RAG + SSE 流式输出 |

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
    └── services/        # 业务逻辑 (RAG, embedding, vector store, LLM)
```

## 核心模块

- **笔记管理**: `backend/app/api/routes/notes.py` - 支持双向链接 (`[[标题]]` 语法)
- **知识图谱**: `backend/app/api/routes/graph.py` - 全局/局部图谱可视化
- **AI 问答**: `backend/app/services/rag_chain.py` - RAG 检索 + 流式输出
- **向量检索**: `backend/app/services/vector_store.py` - FAISS 向量索引 + 混合检索
- **Prompt 系统**: PromptLab + Skill Chain + Few-Shot 学习

## 数据模型

核心实体关系：
- User → Notes (一对多)
- Folder → Notes (一对多，支持 4 层嵌套)
- Category → Folders (一对多，三大分类：个人/工作/素材)
- Note ↔ Tag (多对多)
- Note ↔ Note (双向链接，通过 `linked_note_ids` 字段)

## 环境变量

后端需要配置 `backend/.env` 文件（参考 `.env.example`）：
- `DASHSCOPE_API_KEY` - 阿里云 DashScope API（向量化）
- `JWT_SECRET_KEY` - JWT 认证密钥
- `DATABASE_URL` - SQLite 数据库路径
- `FAISS_INDEX_PATH` - 向量索引路径

## API 路由前缀

所有 API 路由均以 `/api` 为前缀，主要端点：
- `/api/notes` - 笔记 CRUD
- `/api/folders` - 文件夹管理
- `/api/tags` - 标签管理
- `/api/search` - 搜索 + AI 问答
- `/api/graph` - 知识图谱
- `/api/skills` - Skill 执行引擎
- `/api/prompts` - Prompt 管理
