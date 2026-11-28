# 知枢星图后端

Python 3.11 + FastAPI + SQLAlchemy + LangGraph 服务，提供笔记、检索、知识图谱、Agentic RAG、MCP 与评估能力。项目总览见 [../README.md](../README.md)。

## 环境与启动

```bash
cd backend
uv venv --python <Python 3.11+> --system-site-packages .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
cp .env.example .env
```

编辑 `.env` 后启动：

```bash
# Windows 本机必须使用此脚本，裸 uvicorn 会卡在 WMI 查询
.venv\Scripts\python.exe -u start_dev.py

# 其他环境可使用标准入口
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

服务地址：`http://127.0.0.1:8000`，交互式接口文档：`http://127.0.0.1:8000/docs`。

## 关键环境变量

完整配置见 [.env.example](.env.example)。

| 变量 | 默认值/用途 |
|------|-------------|
| `DATABASE_URL` | SQLite 数据库路径 |
| `JWT_SECRET_KEY` | JWT 认证密钥 |
| `DEEPSEEK_API_KEY` | Agent 推理与 DeepSeek Search/Fetch |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` |
| `DEEPSEEK_THINKING` | Agent 工具调用必须设为 `disabled` |
| `DASHSCOPE_API_KEY` | DashScope 向量化 |
| `QWEN_EMBEDDING_MODEL` | `qwen3.7-text-embedding` |
| `WEB_SEARCH_PROVIDER` | `deepseek`（默认）；`tavily` 为回滚通道 |
| `DEEPSEEK_SEARCH_TIMEOUT` | Search 超时，默认 20 秒 |
| `DEEPSEEK_FETCH_TIMEOUT` | Fetch 超时，默认 25 秒 |
| `TAVILY_API_KEY` | 仅 `WEB_SEARCH_PROVIDER=tavily` 时需要 |
| `JUDGE_PROVIDER` | `glm`（默认）；`qwen` 为回退裁判 |
| `GLM_API_KEY` / `GLM_JUDGE_MODEL` | GLM 评估裁判配置 |
| `AGENT_MULTI_AGENT` | 多 Agent 平铺图开关；`start_dev.py` 默认开启 |
| `AGENT_TOKEN_BUDGET` | 单轮 ReAct token 上限，默认 55000 |
| `AGENT_SESSION_TOKEN_BUDGET` | 单会话 token 上限，默认 200000 |
| `CORE_INTENT_ENABLED` | `off` / `shadow` / `on`，默认 `on` |
| `MCP_API_KEY` | MCP 认证；为空时拒绝所有 `/mcp` 请求 |
| `MCP_ENABLE_WRITE` / `MCP_WRITE_USER_ID` / `MCP_DRY_RUN` | MCP 写工具三重闸门，默认关闭 |
| `USE_LANGCHAIN_VECTORSTORE` | 必须与 FAISS 索引格式一致；现网原生索引保持 `false` |

## 测试

```bash
# Windows 本机：测试需进程内 platform workaround，且禁用 xdist
.venv\Scripts\python.exe -m pytest tests/ -q -p no:xdist

# 双链 JSON → note_links 回填（幂等）
.venv\Scripts\python.exe scripts/migrate_note_links.py
```

当前后端测试基线：**472 passed**（2026-11-28）。

`/api/agent/chat/stream` 在 `final_answer` 后按需发送 `sources` SSE 事件（含 `session_id`、`message_id`、`sources`）；历史助手消息返回相同来源数组。来源保存端点不重新抓取网页，重复请求由 `agent:{session_id}:source:{source_id}` 幂等键返回同一篇笔记。

## 主要接口

所有业务接口以 `/api` 为前缀：

```text
POST /api/auth/login
GET/POST/PUT/DELETE /api/notes
GET  /api/notes/{id}/backlinks
GET  /api/notes/{id}/unlinked-mentions
GET  /api/search
GET  /api/search/hybrid
POST /api/search/ai
POST /api/agent/chat/stream
GET  /api/agent/sessions
GET  /api/agent/sessions/{id}/messages
GET  /api/agent/sessions/{id}/recovery
POST /api/agent/sessions/{id}/sources/{source_id}/save
GET/POST /api/agent/sessions/{id}/tasks
POST /api/agent/sessions/{id}/tasks/{tid}/switch
POST /api/agent/sessions/{id}/tasks/{tid}/restore
POST /api/agent/resume
GET  /api/graph/global
GET  /api/graph/local/{id}
POST /mcp
```

## 目录结构

```text
backend/
├── app/
│   ├── api/routes/       # HTTP 路由
│   ├── core/             # 配置与安全
│   ├── db/               # 数据库会话
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic 模型
│   └── services/         # Agent、RAG、工具、评估与可观测
├── eval/                 # 评测集、运行器与报告
├── scripts/              # 迁移与验证脚本
├── tests/                # pytest 测试
├── requirements.txt
└── start_dev.py          # Windows 本机开发启动垫片
```

更多架构与运维说明见 [CODE_WIKI.md](../docs/CODE_WIKI.md) 和 [启动文档.md](../docs/启动文档.md)。

## License

项目声明 MIT；仓库当前未附 `LICENSE` 文件。
