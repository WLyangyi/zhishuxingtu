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

# 启动开发服务器（本机 Windows 必须用 start_dev.py，裸 uvicorn 会卡死在 WMI 查询）
.venv\Scripts\python.exe -u start_dev.py

# 运行测试（本机需进程内注入 platform workaround，见 docs/启动文档.md §4.2）
.venv\Scripts\python.exe -m pytest tests/ -q -p no:xdist

# 双链 JSON → note_links 回填（幂等；改双链存储后重跑）
.venv\Scripts\python.exe scripts/migrate_note_links.py
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

# CI 门禁四件套（frontend-gate.yml 同款）
npm run lint:hex
npx vue-tsc --noEmit
npm run test:run
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.4 + TypeScript + Pinia + vue-router + Tailwind CSS + D3 + Reka UI（naive-ui / gsap / lenis / sass 均已移除；P0–P6 已完成）。**本地补充约定：`docs/design/前端规范.md`（不入库；若本机存在则改前端 UI 前先读）**，判定指南：原则 + 理由 + 反例；视觉值唯一真相为 `frontend/src/styles/tokens.css` |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + FAISS + LangChain + LangGraph |
| AI | DeepSeek agent（LangGraph 编排器 + 4 专职子 Agent + ReAct + 三查）+ qwen Embedding/裁判 + RAG + SSE |

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
- **Agentic RAG**: `backend/app/services/agent/` + `llm/` + `tools/` - 编排器（`intent_classify` 四分类 + `route_intent_multi`）路由 4 专职子 Agent（chat / knowledge / web_research / note_write），工具与提示词由 `AGENT_CONFIGS` 按 `current_agent` 查表（knowledge 移出写入工具、note_write 结构强制查重、三查按 agent 裁剪）；`AGENT_MULTI_AGENT` 开关双图共存（false=单图回退位）；`execute_tool` 对重复检索/永久不可用工具/未查重写入三道熔断防死循环；写工具幂等键（`agent:{session_id}:{tool_call_id}`）防重放重复落库。`intent_classify` 同次结构化输出 core_intent 锚点（init/append/revise/none 迁移表裁决，锚点以稳定 id SystemMessage 注入 messages，`render_anchor` 保一致），`CORE_INTENT_ENABLED` off/shadow/on 三模式一键回滚；二期 task 分层：`agent_tasks` 表（`WHERE status='active'` 部分唯一索引）+ 锚点下沉 task（`state_anchor_key` 切 task 替换锚点、无残留双锚）+ clarify/new_task 四分类闭环（`handle_clarification`，new_task 切任务+旧任务完成、revise 改锚点）
- **MCP Server**: `backend/app/services/mcp_server.py` - 知识库 MCP 化（`/mcp` 端点，API Key 认证，与 agent 共享工具层）
- **AI 问答**: `backend/app/services/rag_chain.py` - RAG 检索 + 流式输出（agent 降级 fallback）
- **向量检索**: `backend/app/services/vector_store.py` - FAISS 向量索引 + 混合检索
- **评估体系**: `backend/eval/` + `services/llm/judge_metrics.py` - 50 条 eval set（含 `expected_intent` 标注）+ 14 条意图边界用例 + `QWEN_JUDGE_MODEL` 独立裁判（P22 坏输出容错）+ 延迟/token/路由准确率口径（`run_eval.py` 新旧对比，报告在 `eval/reports/`）
- **Prompt 系统**: PromptLab + Skill Chain + Few-Shot 学习

## 前端红线与约定
- **本地补充约定**：`docs/design/前端规范.md`（本机文档、不入库；存在则新增/改动 UI 前先读）。原则 + 理由 + 反例的判定指南，不写具体值（值查 `frontend/src/styles/tokens.css`）。尤其注意"领域 UI 抽 domain 组件 + 四态齐备"，锚点卡片是已知欠账、不是样板。
- 叶子组件的渲染错误会冻结整棵组件树：独立区域用 `ErrorBoundary` 包裹；Teleport/portal 内容不在组件树内，这类错误靠 `main.ts` 全局 `errorHandler` 兜底。
- 新增具名路由会被 `tests/smoke.routes.spec.ts` 自动覆盖；测试 mock 走 `@/api` 边界且**必须返回 Promise**（否则 `.catch` 链 TypeError 会被吞成 notFound）。
- 视觉值只走 CSS 令牌（`npm run lint:hex` 为门禁）；测试用 `npm run test:run`，不要去掉 `--no-file-parallelism`（本机并行 worker 会 SIGTERM）。

## 数据模型

核心实体关系：
- User → Notes (一对多)
- Folder → Notes (一对多，支持 4 层嵌套)
- Category → Folders (一对多，三大分类：个人/工作/素材)
- Note ↔ Tag (多对多)
- Note ↔ Note (双向链接：`note_links` 关联表是出链/反链/图谱的查询入口；`notes.linked_note_ids` JSON 仅回滚保险，写路径同步维护)
- agent_sessions / agent_tool_calls - Agent 会话与工具调用审计（M1；`agent_route` 命中路由 M7.4）。agent_sessions 含 core_intent 锚点字段：`core_intent`（JSON `{goal, constraints, acceptance_criteria}`，checkpoint 是唯一真相源、本列是查询镜像）、`intent_version`（每次变更 +1）、`intent_versions`（变更历史快照，含 version/change_type/source/confidence/unmapped_keys）
- agent_tasks - Agent 任务分层（二期 2.1）：一会话可挂多任务，`WHERE status='active'` 部分唯一索引（同会话仅一个 active）；`phase`（执行阶段 clarify/executing/review/done）与 `status`（生命周期 active/completed/cancelled/archived）职责分离；core_intent 从 session 下沉到 task（goal/constraints/acceptance_criteria/intent_version/intent_versions），`depends_on` 支持 new_task 依赖；session 级 intent_versions 作 legacy 不动
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
- `JUDGE_PROVIDER=glm` / `GLM_JUDGE_MODEL=glm-5.3-flash` - 默认评估裁判；qwen 回退用 `JUDGE_PROVIDER=qwen` + `QWEN_JUDGE_MODEL=qwen3.7-max-2026-06-08`（跨裁判分数不可直接比较）
- `AGENT_MULTI_AGENT=false` - M7 A′ 多 Agent 图开关（true=编排器路由 4 子 Agent 的平铺图，false=单 Agent 图回退位）
- `CORE_INTENT_ENABLED=on` - core_intent 意图锚点开关：`off`=回滚旧 QueryIntent schema 不注入锚点（state.core_intent 保留但忽略、清理锚点消息、/sessions /messages 不返回）、`shadow`=只算不写不注入（指标存日志）、`on`=写 state + 注入锚点。改 .env 一键回滚，非法值回退 on
- `AGENT_TOKEN_BUDGET=30000` - 单轮 ReAct token 硬上限（勿调回 10000：note_write 多轮工具链约 21000，过低会在已生成 create_note 后误杀写入；仍须低于会话级 `AGENT_SESSION_TOKEN_BUDGET`）
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` - 可观测（M2，fail-silent；trace 上报遗留，需干净 `.venv-clean`）
- `MCP_API_KEY` - MCP Server `/mcp` 认证（M3，为空则 fail-closed 拒绝所有请求）
- `MCP_ENABLE_WRITE` / `MCP_WRITE_USER_ID` / `MCP_DRY_RUN` - MCP 写工具三重闸门（默认全关：ENABLE_WRITE=true 且 WRITE_USER_ID 非空才暴露 `create_note`；DRY_RUN=true 只回预览不落库。本机当前为真写）
- `USE_LANGCHAIN_VECTORSTORE` - 必须与 FAISS 索引格式一致：现网索引是 `index.faiss + meta.json`（原生 store），置 true 会因缺 `index.pkl` 加载失败、检索恒空
- `TAVILY_API_KEY` - web_search 联网搜索（M3，为空则工具优雅降级）

## API 路由前缀

所有 API 路由均以 `/api` 为前缀，主要端点：
- `/api/notes` - 笔记 CRUD（含 `GET /notes/{id}/backlinks` 反链、`GET /notes/{id}/unlinked-mentions` 未链接提及）
- `/api/folders` - 文件夹管理
- `/api/tags` - 标签管理
- `/api/search` - 搜索 + AI 问答
- `/api/graph` - 知识图谱
- `/api/skills` - Skill 执行引擎
- `/api/prompts` - Prompt 管理
- `/api/agent/chat/stream` - Agent ReAct 问答（SSE 流式）
- `/api/agent/sessions` - Agent 会话管理（`?q=` 标题关键词过滤、`?limit=` 条数上限；`on` 模式返回 core_intent 锚点摘要 goal+version）
- `/api/agent/sessions/{id}/messages` - 会话消息（过滤锚点 SystemMessage；`on` 模式额外返回完整 core_intent）
- `/api/agent/sessions/{id}/tasks` - 任务列表（`GET`）/创建任务（`POST`，建 active、旧 active 完成）
- `/api/agent/sessions/{id}/tasks/{tid}/switch` - 切换当前任务（旧 active 完成、目标激活、写入图状态 current_task_id）
- `/api/agent/sessions/{id}/tasks/{tid}/restore` - 恢复非 active 任务
- `/api/agent/resume` - 审批恢复（`Command(resume=...)`，理由可合并约束/偏好进锚点）

## 深入文档

- [Code Wiki](docs/CODE_WIKI.md) — 代码架构全览（模块职责、核心类/函数、API 路由）
- [启动文档](docs/启动文档.md) — Windows/Anaconda 环境启动指南与故障排查
- [产品需求文档 (PRD)](docs/superpowers/specs/prd.md)
- [技术架构](docs/superpowers/specs/技术架构.md) — 含 §4.19 Agentic RAG 多 Agent 架构（架构图/子 Agent 策略/防御熔断）
- [Agentic RAG 升级笔记](docs/agentic-rag-upgrade/升级笔记.md) — Agentic RAG 升级的决策/踩坑/进展（持续维护）
- [Agentic RAG 实施计划](docs/agentic-rag-upgrade/实施计划.md) — M0-M7 执行步骤清单（含验收标准与 eval 硬门槛）
- [M7 多 Agent 协作计划](docs/agentic-rag-upgrade/多Agent协作计划.md) — 三方案对比 / A′ 平铺图定稿 / P0 风险清单 / 决策拍板
- [Agentic RAG 待做清单](docs/agentic-rag-upgrade/待做清单.md) — 收尾遗留与新发现缺陷（含 M7 盘点）
- [升级开发文档](docs/upgrade-2026-11-18/升级开发文档.md) — 前端重构收官后的下一阶段路线图（P0 稳健性加固 / P1 数据层与测试 / P2 体验增强，含验收标准）
- [状态管理升级路线图](docs/状态管理升级/roadmap.md) — core_intent 意图锚点三期交付路线（一期单任务锚点/二期 task 分层/三期恢复核对+幂等），含当前进度与验收门禁；同目录有改造方案 v7、开发实施文档（TDD）、开发笔记
