# 知枢星图 - 个人知识库系统

> 🚀 双向链接 + 知识图谱 + **Agentic RAG 智能问答**：编排器 + 4 专职子 Agent，从"搜一次就答"到"自主检索、三查自检、效果可量化"

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vue 3.4+](https://img.shields.io/badge/Vue-3.4%2B-brightgreen)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-blue)](https://fastapi.tiangolo.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-112%20passed-brightgreen)](backend/tests/)

## ✨ 核心亮点：多 Agent Agentic RAG

AI 问答不是简单的"检索一次喂给大模型"，而是一个 LangGraph 驱动的**编排器 + 4 专职子 Agent** 架构（平铺图实现，`AGENT_MULTI_AGENT` 开关与单 Agent 图双图共存、一键回退）：

```mermaid
flowchart TD
    Q[用户问题] --> I{编排器 · 意图四分类<br/>fail-safe 兜底}
    I -->|direct_answer 常识闲聊| C[chat_agent<br/>短路直答省 token]
    I -->|knowledge| K[knowledge_agent<br/>知识检索 + 三查反思]
    I -->|web_search| W[web_research_agent<br/>联网优先 · 信源引用 · 仅幻觉查]
    I -->|note_write| N[note_write_agent<br/>结构强制查重 → 写入]
    C --> O[SSE 流式输出]
    K --> T1[检索 / 图谱 / 联网回退]
    T1 --> G{三查 · 强制节点}
    G -->|不相关 / 无出处 / 答非所问| RW[查询改写重搜]
    G -->|全部通过| O
    W --> T2[web_search 专职] --> HC[幻觉查] --> O
    N --> T3[查重 search_notes] --> H[interrupt 人工审批] -->|批准| W3[create_note] --> O
```

- **🎯 编排器 + 4 专职子 Agent** - 入口 LLM 结构化输出意图四分类（fail-safe 兜底），各子 Agent **工具面收窄 + 专属提示词**：知识 Agent 移出写入工具（联网保留作误判回退）、联网 Agent 信源标注 + 仅幻觉查、写入 Agent 人工审批即质量关；**14 条意图边界用例集回归**（3 轮多数票 100%），路由准确率 **98%**
- **🪞 Self-RAG 三查反思** - 资料相关性 / 幻觉检测 / 答案质量实现为**图强制节点 + 条件边**（结构保证每轮必检），并按子 Agent 裁剪：联网仅幻觉查、写入以人工审批为质量关
- **🛡️ 结构兜底优于提示词恳求** - 实测模型会无视"先查重再写入"的流程指令，`execute_tool` 以结构拦截未查重的写入请求（复用熔断模式，错误恢复遵从性 > 预防性指令遵从性）
- **🛑 防失控四道闸** - 最大迭代 + token 预算双硬截断、同轮重复检索短路、不可用工具熔断、编排意图提示仅首轮注入（防反复推回同一路由）；Agent 异常自动降级混合检索兜底链路
- **↩️ 双图回退开关** - `AGENT_MULTI_AGENT` 多 Agent 图 / 单 Agent 图共存，改 .env 一键回滚；50 条评测实测**双图行为等价**（回退零风险），命中路由入库审计（`agent_route` 分布入可观测面板）
- **📊 量化评估体系** - 50 条六类离线评测集（含 `expected_intent` 标注 + 路由准确率口径）+ 延迟 mean/P95 + token/成本口径；recall@k 纯计算 + 4 个独立裁判指标（faithfulness / answer_relevancy / context_recall / answer_coverage，判决模型与生成模型不同源：默认 GLM-5.3-Flash，坏输出容错）+ 10 条人工校准（裁判一致率 90% / 100%）；质量门禁 `eval_gate.py`（CI 阻断）+ 7 组消融
- **🔌 知识库 MCP 化** - FastMCP 3.x 挂载 FastAPI（`/mcp` 端点），API Key timing-safe 认证、未配置 fail-closed；与 Agent 共享同一工具层，Claude Desktop / Cursor 可直连检索（验证脚本 7/7 通过）
- **✍️ 写入人工审批（HITL）** - 笔记写入走 LangGraph interrupt，SSE 审批卡 + POST resume，中断状态可恢复（409 防串扰），工具调用全量审计
- **🧠 双层记忆** - 短期 checkpoint（会话内多轮）+ 长期 store（跨会话用户偏好），LangGraph 官方标准模型
- **👁️ 双源可观测** - Langfuse 云端优先 + 本地审计自动降级，前端实时展示 Thought / Action / Observation / Check 推理时间线
- **🔬 差异化方案先验证再上线** - GraphRAG-lite（双向链接 1 跳邻居 + RRF，落在工具层、一键回退）与 Contextual Retrieval（LLM 生成定位前缀后重索引，独立对照索引）都已实现并各自配了消融/对照实验；在本机语料（18 篇笔记、0 条双向链接、9 条向量）上两者对 recall 均**无可测增益**（top-5 命中集不变），故不切换生产索引、只保留可复现实验——"做了但不上线"同样是结论

### 📈 评测结果（50 条六类离线评测集，报告可复现）

| 指标 | 基线 RAG | Agentic RAG | 说明 |
|------|:---:|:---:|------|
| recall@k | 0.993 | 0.983 | 纯计算，不依赖裁判 |
| faithfulness | 0.957 | 0.922 | 独立裁判（GLM-5.3-Flash） |
| answer_relevancy | 0.973 | 0.971 | 独立裁判 |
| context_recall | — | 0.977 | 独立裁判，检索证据能否撑起标准答案 |
| answer_coverage | — | 0.976 | 独立裁判，答案覆盖了标准答案多少要点 |
| pass 率 | — | 45/50 = 90% | 5 指标 + 路由单条判定 |
| 路由准确率 | — | 100%（50/50） | vs 标注的 `expected_intent` |
| 平均 token / 延迟 | — | 8426 / 8942 ms（P95 12239） | 端到端 `graph.stream` |

**M7 多 Agent 双图对比**（旧裁判 `qwen3.7-plus-2026-05-26`，同裁判各 50 条全量；只用于两张图之间比较，不与上表跨裁判比较）：

| 指标 | 单 Agent 图（回退） | 多 Agent 图（A′） |
|------|:---:|:---:|
| recall@k / faithfulness / relevancy | 0.962 / 0.845 / 0.918 | 0.962 / **0.879** / **0.936** |
| 路由准确率（vs expected_intent） | 98% | **98%** |
| 平均 token 消耗 | 9370 | **9239** |
| 平均工具调用 | 3.68 | 3.52 |

> 口径说明：主表 = 2026-10-27 冻结的全量基线（裁判 GLM-5.3-Flash，5 指标 + pass/路由/成本，报告 `backend/eval/reports/2026-10-27-comparison.md`）；跨裁判分数不可直接比较，旧裁判时代的分数只保留双图同裁判对比（M7 表）。相对旧基线，本轮 recall 持平、faithfulness +0.013、路由 98%→100%、token/延迟双降；pass 率 90%（5 条未通过：q017 答非所问、q019/q050 幻觉、q039 少召回一篇、q034 证据不足）；其中只有 q034 是新增的 context_recall / answer_coverage 才抓出来的——它在旧口径的 recall / faithfulness / relevancy 上全部达标，这正是补指标的意义。
>
> 门禁：`python eval/eval_gate.py` 读最新摘要按 7 项阈值判定，exit 0/1 直接用于 CI 阻断；本地已验证「放行达标」与「拦住人为回退」两条路径。

## ✨ 功能特性

### 🎯 知识管理
- **📝 笔记管理** - Markdown 编辑器，分屏预览，语法高亮
- **🔗 双向链接** - `[[笔记标题]]` 语法，建立知识关联
- **🕸️ 知识图谱** - 全局/局部图谱可视化（D3），图谱邻居可作为 Agent 检索工具
- **🔍 混合检索** - 向量语义检索 + 关键词检索融合

### 🤖 AI 能力
- **Agentic RAG 智能问答** - 见上方核心亮点，SSE 流式输出
- **联网搜索** - Tavily 集成，限速 + TTL 缓存 + 缺 Key 优雅降级（不阻塞主流程）
- **结构化输出** - function_calling 方式结构化判定，规避 response_format 兼容问题
- **Prompt / Skill 系统** - PromptLab + Skill 执行引擎 + Few-Shot 学习

### 🛡️ 安全
- **JWT 认证** + 环境变量管理敏感配置（API Key 不进代码 / 前端）
- **MCP fail-closed** - MCP_API_KEY 未配置时拒绝所有外部请求，宁可全拒不能裸奔
- **写入人工审批** - 有副作用的工具操作需人工批准
- **提示注入隔离** - 导入的网页 / PDF 内容以不可信数据边界包裹

## 🏗️ 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3.4 · TypeScript · Pinia · Naive UI · Tailwind CSS · D3 |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy · SSE |
| AI 编排 | LangGraph 0.2.x（编排器 + 4 专职子 Agent / ReAct / 三查 / HITL / checkpoint / 双图回退开关）· LangChain |
| 模型 | DeepSeek-V4-flash（Agent 推理，显式关思考）· qwen3.7-text-embedding（向量化）· GLM-5.3-Flash（独立评估裁判，JSON mode + 坏输出容错） |
| 数据 | FAISS（向量索引 + 混合检索）· SQLite · Redis |
| 生态 | FastMCP 3.x（MCP Server）· Tavily（联网搜索）· Langfuse（可观测）· pytest（后端 112 用例） |

## 🚀 快速开始

### 环境要求
- Python 3.11+（推荐用 uv 管理依赖）
- Node.js 18+

### 1. 克隆与后端配置
```bash
git clone <your-repo-url>
cd 知枢星图/backend

python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

cp .env.example .env         # 编辑 .env 填入你的 API Key
```

`.env` 关键配置（完整项见 `.env.example`）：
```env
# Agent 推理（DeepSeek 官方通道，thinking 显式关闭）
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=disabled

# 向量化（阿里云 DashScope）
DASHSCOPE_API_KEY=your-dashscope-api-key
QWEN_EMBEDDING_MODEL=qwen3.7-text-embedding

# 评估独立裁判（与推理模型不同源；glm=智谱 GLM-5.3-Flash，qwen=回退千问）
JUDGE_PROVIDER=glm
GLM_API_KEY=your-zhipu-api-key
GLM_JUDGE_MODEL=glm-5.3-flash

# 多 Agent 编排（true=编排器路由 4 专职子 Agent，false=单 Agent 图回退位）
AGENT_MULTI_AGENT=true

# 联网搜索（Tavily 免费注册 https://tavily.com；为空则工具优雅降级）
TAVILY_API_KEY=tvly-xxx

# MCP Server 认证（为空则拒绝所有 MCP 请求）
MCP_API_KEY=your-mcp-api-key

# 可观测（可选，fail-silent）
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

### 2. 启动
```bash
# 后端
python -m uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd ../frontend
npm install
npm run dev
```

打开 `http://localhost:5173`，在「AI 助手」发起问答即可看到完整的推理时间线。

### 3. Docker 容器化启动（可选）

```bash
cp backend/.env.example backend/.env     # 先填 API Key（密钥不进镜像）
docker compose up -d --build
docker compose ps                        # backend 显示 healthy 即就绪
```

- 前端 `http://localhost:8080`（nginx 托管静态资源，`/api` 反代到后端且关闭 SSE 缓冲）
- 后端 `http://localhost:8000/docs`，健康检查 `/health`
- SQLite / FAISS / checkpoint 落命名卷 `zhishu-data`，重建容器不丢数据

### 4. 验证脚本（推荐先跑）
```bash
python scripts/verify_deepseek_tools.py       # 模型工具调用契约 4/4
python scripts/verify_mcp_server.py           # MCP Server 全链路 7/7
python scripts/verify_web_search.py           # 联网搜索（含降级模式）5/5
python scripts/verify_multi_agent_skeleton.py # 多 Agent 骨架真实链路（SSE 契约 + 跨轮隔离）
python scripts/verify_m73_specialists.py      # 专职子 Agent 全流程（联网路由 + 写入审批/拒绝）15/15
python scripts/probe_intent_boundary.py       # 意图边界用例集路由准确率（14 条 × N 轮）
python eval/run_eval.py                       # 50 条评测集新旧对比（recall/裁判/延迟/token）
python eval/eval_gate.py                      # 回归门禁：校验最新基线摘要是否达标（CI 同款，exit 0/1）
python eval/ablation_runner.py                # 7 组消融（默认 --skip-judge，只比 recall/路由/延迟/token）
python eval/run_behavior_eval.py              # Agent 行为评测 10 条（拒答/越权/注入/澄清/多轮/熔断）
```

## 🔌 API 接口

```
# 认证 / 笔记 / 文件夹 / 标签
POST /api/auth/login            GET/POST/PUT/DELETE /api/notes
GET  /api/notes/:id/backlinks   # 反向链接

# 检索
GET  /api/search                # 全文搜索
POST /api/search/hybrid         # 混合检索
POST /api/search/ai             # RAG 问答（基线链路）

# Agentic RAG
POST /api/agent/chat/stream     # Agent 问答（SSE 流式：thought/action/observation/check/final_answer）
GET  /api/agent/sessions        # 会话管理
POST /api/agent/resume          # HITL 审批恢复
GET  /api/agent/traces          # 可观测 trace
GET  /api/agent/observability/summary

# 知识图谱
GET  /api/graph/global          GET /api/graph/local/:id

# MCP Server（API Key 认证，Claude Desktop / Cursor 直连）
POST /mcp
```

## 🗺️ 版本演进

```
V1 MVP          V2 分类升级       V3 Skill         V4 扩展           V5 Agentic RAG (2026.08)
  │                │                │                │                 │
  ▼                ▼                ▼                ▼                 ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────────────┐
│ 笔记管理 │    │ 分类体系 │    │ Skill   │    │ 语义搜索 │    │ M0 embedding 迁移│
│ 文件夹   │ -> │ 内容类型 │ -> │ 执行引擎│ -> │ 导入导出 │ -> │ M1 ReAct + 三查  │
│ 标签     │    │ 素材管理 │    │ AI生成  │    │ 浏览器插件│   │ M2 评估 + 可观测 │
│ 双向链接 │    │ 模板系统 │    │ 自动化  │    │ 批量处理 │    │ M3 MCP + 联网    │
│ 知识图谱 │    │          │    │         │    │          │    │ M4 记忆 + HITL   │
│ AI问答   │    │          │    │         │    │          │    │ M5 监控面板      │
│          │    │          │    │         │    │          │    │ M6 意图路由      │
│          │    │          │    │         │    │          │    │ M7 多Agent编排   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └──────────────────┘
```

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件
