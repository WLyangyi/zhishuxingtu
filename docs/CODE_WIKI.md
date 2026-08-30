# 知枢星图 - Code Wiki

> 本文档为知枢星图项目的完整代码架构文档，包含项目整体架构、主要模块职责、关键类与函数说明、依赖关系以及项目运行方式等关键信息。

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [项目架构](#3-项目架构)
4. [后端模块详解](#4-后端模块详解)
5. [前端模块详解](#5-前端模块详解)
6. [核心服务层](#6-核心服务层)
7. [数据库模型](#7-数据库模型)
8. [API路由](#8-api路由)
9. [依赖关系](#9-依赖关系)
10. [运行方式](#10-运行方式)

---

## 1. 项目概述

知枢星图是一个现代化的**个人知识资产管理平台**，支持以下核心功能：

- **笔记管理** - Markdown编辑器，支持双向链接语法 `[[笔记标题]]`
- **知识图谱** - 全局/局部图谱可视化
- **智能检索** - 全文搜索 + AI智能问答
- **RAG检索增强生成** - 基于知识库的AI问答
- **Skill智能模块** - 可执行的AI技能包
- **混合检索** - 向量 + BM25融合，Reranker重排序

---

## 2. 技术栈

### 前端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4+ | 渐进式JavaScript框架 |
| TypeScript | 5.x | 类型安全的JavaScript |
| Pinia | 2.1.7+ | Vue状态管理 |
| Naive UI | 2.38.1+ | Vue 3组件库 |
| Tailwind CSS | 3.4+ | 原子化CSS |
| Vue Router | 4.3+ | Vue路由管理 |
| D3.js | 7.9+ | 知识图谱可视化 |
| Vite | 5.1+ | 构建工具 |
| Markdown-it | 14.0+ | Markdown解析 |

### 后端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 高性能后端语言 |
| FastAPI | 0.115+ | 现代Web框架 |
| SQLAlchemy | 2.0+ | ORM框架 |
| Pydantic | 2.10+ | 数据验证 |
| FAISS | 1.9+ | Facebook开源向量索引 |
| LangChain | 0.3+ | RAG应用开发框架 |
| LangGraph | 0.2.x（锁<0.3） | Agent 图编排（编排器 + 4 专职子 Agent + ReAct 循环 + 三查强制节点，双图回退开关） |
| DashScope | 1.20+ | 阿里云文本向量化（qwen3.7）+ 评估裁判（QWEN_JUDGE_MODEL，现为 qwen3.7-plus-2026-05-26） |
| OpenAI | 1.50+ | LLM调用（DeepSeek 官方通道，agent 推理） |
| langfuse | 4.x | 可观测（M2，fail-silent，trace 上报遗留） |

---

## 3. 项目架构

```
知枢星图/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                     # API路由层
│   │   │   ├── routes/              # 路由实现
│   │   │   ├── deps.py              # 依赖注入
│   │   │   └── __init__.py          # 路由汇总
│   │   ├── core/                    # 核心配置
│   │   │   ├── config.py            # 配置管理
│   │   │   ├── security.py          # 安全认证
│   │   │   └── exceptions.py        # 异常处理
│   │   ├── db/                      # 数据库层
│   │   │   ├── base.py              # SQLAlchemy基类
│   │   │   └── session.py           # 会话管理
│   │   ├── models/                  # 数据模型
│   │   │   ├── note.py              # 笔记模型
│   │   │   ├── folder.py            # 文件夹模型
│   │   │   ├── category.py          # 分类模型
│   │   │   ├── tag.py               # 标签模型
│   │   │   ├── user.py              # 用户模型
│   │   │   ├── skill.py             # 技能模型
│   │   │   └── ...
│   │   ├── schemas/                 # Pydantic模型
│   │   ├── services/                # 业务逻辑层
│   │   └── main.py                  # 应用入口
│   ├── migrations/                  # 数据库迁移
│   ├── scripts/                     # 工具脚本
│   ├── requirements.txt             # Python依赖
│   └── start.bat                    # 启动脚本
│
└── frontend/                         # Vue 3 前端
    ├── src/
    │   ├── api/                     # API客户端
    │   ├── components/              # Vue组件
    │   │   ├── common/              # 通用组件
    │   │   ├── layout/              # 布局组件
    │   │   └── sidebar/             # 侧边栏组件
    │   ├── views/                   # 页面视图
    │   ├── stores/                  # Pinia状态管理
    │   ├── router/                  # 路由配置
    │   ├── types/                   # TypeScript类型
    │   └── utils/                   # 工具函数
    ├── package.json                  # NPM依赖
    └── vite.config.ts               # Vite配置
```

### 架构分层

```
┌─────────────────────────────────────────────┐
│              前端 (Vue 3)                    │
│   Views → Components → Stores → API Client  │
└─────────────────────────────────────────────┘
                    │ HTTP/REST │ SSE
                    ▼
┌─────────────────────────────────────────────┐
│              后端 (FastAPI)                  │
│   Routes → Services → Models → Database    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│              数据层                          │
│   SQLite + FAISS + BM25                     │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│              外部服务                        │
│   DashScope Embedding + LLM API             │
└─────────────────────────────────────────────┘
```

---

## 4. 后端模块详解

### 4.1 应用入口 - [main.py](file:///d:/知枢星图/backend/app/main.py)

**职责**：FastAPI应用初始化和生命周期管理

**核心功能**：

```python
# 应用初始化配置
app = FastAPI(
    title=settings.APP_NAME,
    description="个人知识库系统 API",
    version="1.0.0",
    lifespan=lifespan  # 生命周期管理
)

# 初始化向量存储
init_vector_store(faiss_path)

# 初始化混合搜索
init_hybrid_search()
```

**关键特性**：
- 生命周期管理：启动时初始化服务，关闭时保存数据
- CORS中间件配置
- 速率限制（slowapi）
- 路由注册

### 4.2 配置管理 - [config.py](file:///d:/知枢星图/backend/app/core/config.py#L1-L109)

**职责**：集中管理应用配置

**配置项分类**：

| 配置类 | 说明 |
|--------|------|
| `APP_NAME` | 应用名称 |
| `DATABASE_URL` | 数据库连接URL |
| `JWT_SECRET_KEY` | JWT密钥 |
| `DASHSCOPE_API_KEY` | 阿里云向量化API密钥 |
| `OPENAI_API_KEY` | LLM API密钥 |
| `FAISS_INDEX_PATH` | FAISS索引路径 |
| `USE_HYBRID_SEARCH` | 是否启用混合检索 |
| `USE_RERANKER` | 是否启用Reranker |
| `MAX_CHUNK_SIZE` | 文本分块大小 |

### 4.3 数据库层

#### 4.3.1 会话管理 - [session.py](file:///d:/知枢星图/backend/app/db/session.py)

```python
# 创建数据库引擎
engine = create_engine(settings.DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 4.3.2 基类定义 - [base.py](file:///d:/知枢星图/backend/app/db/base.py)

```python
class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""

class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=..., onupdate=...)

def generate_uuid():
    """生成UUID字符串"""
    return str(uuid.uuid4())
```

---

## 5. 前端模块详解

### 5.1 应用入口 - [main.ts](file:///d:/知枢星图/frontend/src/main.ts)

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())  // 状态管理
app.use(router)         // 路由

app.mount('#app')
```

### 5.2 状态管理 - [stores/](file:///d:/知枢星图/frontend/src/stores/)

| Store | 说明 |
|-------|------|
| `auth.ts` | 用户认证状态 |
| `notes.ts` | 笔记状态管理 |
| `folders.ts` | 文件夹状态管理 |
| `categories.ts` | 分类状态管理 |
| `tags.ts` | 标签状态管理 |
| `sidebar.ts` | 侧边栏状态 |
| `theme.ts` | 主题管理 |

### 5.3 页面视图 - [views/](file:///d:/知枢星图/frontend/src/views/)

| 视图 | 说明 |
|------|------|
| `Home.vue` | 首页 |
| `NoteEditor.vue` | 笔记编辑器 |
| `GraphView.vue` | 知识图谱 |
| `AIAssistant.vue` | AI助手 |
| `SearchResults.vue` | 搜索结果 |
| `PromptsView.vue` | Prompt管理 |
| `SkillsView.vue` | Skill管理 |
| `Login.vue` | 登录页面 |

---

## 6. 核心服务层

### 6.1 向量存储服务 - [vector_store.py](file:///d:/知枢星图/backend/app/services/vector_store.py)

**职责**：管理FAISS向量索引

**核心类**：`VectorStore`

| 方法 | 说明 |
|------|------|
| `add_vector(note_id, vector)` | 添加向量 |
| `add_vectors(note_ids, vectors)` | 批量添加向量 |
| `update_vector(note_id, vector)` | 更新向量 |
| `remove_vector(note_id)` | 删除向量 |
| `search(query_vector, k, threshold)` | 向量检索 |
| `batch_search(query_vectors, k, threshold)` | 批量检索 |
| `save()` | 保存索引到磁盘 |
| `rebuild_index(note_ids, vectors)` | 重建索引 |

**使用示例**：

```python
from app.services import get_vector_store, init_vector_store

# 初始化
vector_store = init_vector_store("/path/to/faiss")

# 添加向量
vector_store.add_vector("note_id", embedding)

# 搜索
results = vector_store.search(query_vector, k=5, threshold=0.3)
# 返回: [(note_id, score), ...]
```

### 6.2 向量化服务 - [embedding_service.py](file:///d:/知枢星图/backend/app/services/embedding_service.py)

**职责**：文本向量化

**核心类**：`EmbeddingService`

| 方法 | 说明 |
|------|------|
| `embed_text(text)` | 单条文本向量化 |
| `embed_texts(texts)` | 批量文本向量化 |
| `embed_chunks(note_id, title, content)` | 分块向量化 |
| `prepare_note_text(title, content)` | 准备笔记文本 |

**配置**：
- 模型：`text-embedding-v3`（阿里云DashScope）
- 维度：1024
- API：`https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings`

### 6.3 混合检索服务 - [hybrid_search.py](file:///d:/知枢星图/backend/app/services/hybrid_search.py)

**职责**：融合向量检索和BM25关键词检索

**核心类**：`HybridSearchService`

```python
class HybridSearchService:
    def hybrid_search(
        self,
        query: str,
        db: Session,
        k: int = 10,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        rrf_k: int = 60,
        use_reranker: bool = False
    ) -> List[Tuple[Any, float]]:
        """
        执行混合检索
        使用RRF (Reciprocal Rank Fusion) 算法融合
        """
```

**RRF融合公式**：
```
RRF Score = Σ weight * (1 / (k + rank))
```

### 6.4 BM25检索服务 - [bm25_service.py](file:///d:/知枢星图/backend/app/services/bm25_service.py)

**职责**：BM25关键词检索

**核心类**：`BM25Service`

| 方法 | 说明 |
|------|------|
| `index_documents(docs)` | 构建BM25索引 |
| `add_document(doc_id, title, content)` | 添加文档 |
| `remove_document(doc_id)` | 删除文档 |
| `search(query, top_k)` | BM25检索 |
| `rebuild_index(db)` | 从数据库重建索引 |

**特性**：
- 使用jieba中文分词
- 支持中英文混合分词
- 线程安全

### 6.5 文本分块服务 - [text_chunker.py](file:///d:/知枢星图/backend/app/services/text_chunker.py)

**职责**：智能文本分块

**核心类**：`RecursiveChunker`

```python
class RecursiveChunker:
    def __init__(
        self,
        max_chunk_size: int = 800,      # 最大块大小
        overlap_ratio: float = 0.5,       # 重叠比例
        min_chunk_size: int = 50,         # 最小块大小
        chunk_by_divider: bool = True,    # 按 --- 分割
        chunk_by_heading: bool = True,    # 按标题分割
        chunk_by_paragraph: bool = True,  # 按段落分割
        chunk_by_sentence: bool = True   # 按句子分割
    ):
```

**分割优先级**：
1. 按 `---` 分隔符分割
2. 按 Markdown 标题（#）分割
3. 按段落（空行）分割
4. 按句子分割（保底策略）

### 6.6 RAG链 - [rag_chain.py](file:///d:/知枢星图/backend/app/services/rag_chain.py)

**职责**：检索增强生成

**核心类**：`RAGChain`

```python
class RAGChain:
    def invoke(self, question: str) -> Dict[str, Any]:
        """执行RAG问答"""

    def invoke_with_custom_context(
        self,
        question: str,
        context_docs: List[Tuple[Any, float]]
    ) -> Dict[str, Any]:
        """使用自定义上下文的RAG问答"""
```

**返回格式**：
```python
{
    "answer": "AI生成的答案",
    "context": "使用的上下文",
    "source_documents": [{"id": "...", "title": "..."}]
}
```

### 6.7 流式服务 - [stream_service.py](file:///d:/知枢星图/backend/app/services/stream_service.py)

**职责**：SSE流式输出

**核心方法**：
- `stream_chat()` - 对话流式输出
- `stream_rag()` - RAG问答流式输出

**SSE事件格式**：
```
data: {"type": "content", "text": "..."}  # 内容片段
data: {"type": "sources", "notes": [...]} # 相关笔记
data: {"type": "disclaimer", "text": "..."} # 免责声明
data: {"type": "error", "message": "..."}   # 错误信息
data: [DONE]                               # 结束标记
```

### 6.8 Agentic RAG（LangGraph 多 Agent）- [agent/](file:///d:/知枢星图/backend/app/services/agent/)、[llm/](file:///d:/知枢星图/backend/app/services/llm/)、[tools/](file:///d:/知枢星图/backend/app/services/tools/)

**职责**：编排器 + 4 专职子 Agent（M1 ReAct → M6 意图路由 → M7 多 Agent 交付）

**双图架构**（`services/agent/graph.py`，`AGENT_MULTI_AGENT` 开关切换，行为等价可一键回退）：
- 多 Agent 图（A′）：`START → intent_classify → route_intent_multi` 按 4 个 agent 名分发——`chat_agent`（复用 direct_answer 节点）/ `knowledge_agent` / `web_research_agent` / `note_write_agent`（后三者复用 agent_step）
- 单 Agent 图（回退位）：`route_intent` 两分支（direct_answer | agent_step）

**子 Agent 策略表**（`services/agent/nodes.py` `AGENT_CONFIGS`，按 state.current_agent 查表绑定工具与 system prompt）：

| 子 Agent | 工具 | 三查 |
|---|---|---|
| chat_agent | 无（直答） | 无 |
| knowledge_agent | search_notes/get_note/图谱/标签/目录 + web_search 回退 | 全三查 |
| web_research_agent | web_search + search_notes | 仅幻觉查（`should_continue` 直接分流 generate 绕过 grade_documents；无 answer_quality） |
| note_write_agent | create_note + search_notes | 无（`execute_tool` 结构拦截未查重的写入 + interrupt 人工审批即质量关） |

**三查强制节点**（`with_structured_output` 结构化判断，非工具）：`grade_documents` / `hallucination_check` / `answer_quality`——按 current_agent 在 `should_continue`（节点入边）与 `route_hallucination` 分叉裁剪

**LLM Provider 抽象**（`services/llm/`）：
- `DeepSeekProvider` - deepseek-v4-flash + `thinking:disabled`（P2：思考模式拒绝强制 tool_choice）
- `QwenJudgeProvider` - 裁判模型读 `QWEN_JUDGE_MODEL`（现为 qwen3.7-plus-2026-05-26）+ `enable_thinking:false`（P16）；`judge_metrics.py` 含坏输出容错（P22：重试 1 次后 score=None，不崩 eval）

**工具**（`services/tools/`，LangChain `@tool`）：`search_notes` / `get_note` / `get_graph_neighbors` / `list_tags` / `list_folders` / `web_search` / `create_note`（HITL）

**防御**：`MAX_ITERATIONS=8` + `TOKEN_BUDGET=10000` 硬截断；同轮重复检索短路（`searched_queries`）；web_search 永久熔断；未查重写入拦截（M7.3 结构强制查重）；意图提示/task_brief 仅首轮注入（防路由死循环）；异常降级到旧 `/api/search/ai` 链路。意图/task_brief/turn_start_index/current_agent 等路由状态见 `state.py AgentState`

### 6.9 评估体系 - [eval/](file:///d:/知枢星图/backend/eval/)

**职责**：量化旧基线 vs agent 的效果（M2 交付，M6/M7 持续扩口径）

- `eval_set_v1.json` - 50 条评测题（六类配额，M7.1 起含 `expected_intent` 路由 Ground Truth）
- `intent_boundary_set.json` - 14 条意图边界用例（`probe_intent_boundary.py` 多轮多数票回归）
- `run_eval.py` - 基线 vs agent（`graph.stream`）；recall@k 纯计算 + 裁判打分（faithfulness/relevancy）+ 延迟 mean/P95 + token 消耗 + 路由准确率；`AGENT_MULTI_AGENT` 环境变量切换单/多图同口径对比
- `judge_metrics.py` - `judge_faithfulness`（声明逐条判 grounded）+ `judge_answer_relevancy`（P22 容错）
- 报告：`eval/reports/YYYY-MM-DD-comparison.md`（M7.4 起归档副本如 `2026-08-30-m74-multi.md`）；表：`eval_sets` / `eval_runs`
- **P18 教训**：faithfulness 裁判证据必须用 DB 完整内容（snippet 截断会系统性误判 0）

### 6.10 可观测（Langfuse）- [observability/](file:///d:/知枢星图/backend/app/services/observability/)

**职责**：Langfuse trace/span（M2，fail-silent）

- `langfuse_trace.py` - 惰性初始化 Langfuse handler；`build_stream_config(thread_id)` 供 `graph.stream` 传 callbacks
- key 缺失/异常 → 静默降级，不影响 agent 主流程
- **遗留**：langfuse 4.x 运行时崩溃（P17），trace 上报未通；干净环境 `.venv-clean` 已建

---

## 7. 数据库模型

### 7.1 用户模型 - [user.py](file:///d:/知枢星图/backend/app/models/user.py)

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    notes = relationship("Note", back_populates="user")
```

### 7.2 笔记模型 - [note.py](file:///d:/知枢星图/backend/app/models/note.py)

```python
class Note(Base, TimestampMixin):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    folder_id = Column(String(36), ForeignKey("folders.id"))
    user_id = Column(String(36), ForeignKey("users.id"))
    linked_note_ids = Column(Text)  # JSON格式存储链接的笔记ID

    folder = relationship("Folder", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")
    user = relationship("User", back_populates="notes")
```

### 7.3 文件夹模型 - [folder.py](file:///d:/知枢星图/backend/app/models/folder.py)

```python
class Folder(Base, TimestampMixin):
    __tablename__ = "folders"
    __table_args__ = (
        CheckConstraint('level IN (0, 1, 2, 3)', name='check_folder_level'),
    )

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(String(36), ForeignKey("folders.id"))  # 支持4层嵌套
    level = Column(Integer, default=0)  # 0-3
    category_id = Column(String(36), ForeignKey("categories.id"))
    user_id = Column(String(36), ForeignKey("users.id"))

    parent = relationship("Folder", remote_side=[id], backref="children")
```

### 7.4 分类模型 - [category.py](file:///d:/知枢星图/backend/app/models/category.py)

```python
class Category(Base, TimestampMixin):
    """三大入口分类"""
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)  # 个人/工作/素材
    icon = Column(String(50))
    color = Column(String(7))
    sort_order = Column(Integer)
    is_system = Column(Boolean, default=False)

class ContentType(Base, TimestampMixin):
    """内容类型"""
    __tablename__ = "content_types"

    id = Column(String(36), primary_key=True)
    category_id = Column(String(36), ForeignKey("categories.id"))
    name = Column(String(100))
    field_schema = Column(Text, default="{}")  # JSON Schema

class Content(Base, TimestampMixin):
    """内容条目"""
    __tablename__ = "contents"
```

### 7.5 Skill模型 - [skill.py](file:///d:/知枢星图/backend/app/models/skill.py)

```python
class Skill(Base, TimestampMixin):
    """可执行的AI技能"""
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    name = Column(String(200))
    description = Column(Text)
    input_schema = Column(Text, default="{}")      # 输入JSON Schema
    output_schema = Column(Text, default="{}")     # 输出JSON Schema
    execution_logic = Column(Text, default="{}")   # 执行逻辑
    trigger_type = Column(String(20))              # manual/scheduled
    schedule_config = Column(Text, default="{}")   # Cron配置

    executions = relationship("SkillExecution", back_populates="skill")

class SkillExecution(Base):
    """Skill执行记录"""
    __tablename__ = "skill_executions"

    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey("skills.id"))
    user_id = Column(String(36), ForeignKey("users.id"))
    input_data = Column(Text)
    output_data = Column(Text)
    output_content_id = Column(String(36), ForeignKey("contents.id"))
    status = Column(String(20))  # pending/running/success/failed
```

### 7.6 Agent 会话与工具调用 - [agent_session.py](file:///d:/知枢星图/backend/app/models/agent_session.py)

```python
class AgentSession(Base, TimestampMixin):
    """Agent 会话（id = LangGraph thread_id）"""
    __tablename__ = "agent_sessions"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True)
    title = Column(String(500), default="新会话")

class AgentToolCall(Base, TimestampMixin):
    """Agent 工具调用审计"""
    __tablename__ = "agent_tool_calls"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), index=True)
    tool_name = Column(String(100))
    args_json = Column(Text)
    result_json = Column(Text)
    latency_ms = Column(Integer, default=0)
    status = Column(String(50), default="success")
```

### 7.7 评测模型 - [eval.py](file:///d:/知枢星图/backend/app/models/eval.py)

```python
class EvalSet(Base, TimestampMixin):
    """评测题库"""
    __tablename__ = "eval_sets"
    eval_id = Column(String(20), index=True)  # q001...
    question = Column(Text)
    expected_answer = Column(Text)
    relevant_doc_ids = Column(Text)  # JSON 数组
    category = Column(String(50))

class EvalRun(Base, TimestampMixin):
    """评测成绩单"""
    __tablename__ = "eval_runs"
    eval_set_id = Column(String(36), index=True)
    agent_version = Column(String(50))  # baseline / agent-v1
    metrics_json = Column(Text)  # {recall@k, faithfulness, answer_relevancy}
```

---

## 8. API路由

### 8.1 路由汇总

所有路由统一挂载在 `/api` 前缀下：

```python
app.include_router(auth_router, prefix="/api")           # 认证
app.include_router(notes_router, prefix="/api")           # 笔记
app.include_router(folders_router, prefix="/api")        # 文件夹
app.include_router(tags_router, prefix="/api")            # 标签
app.include_router(search_router, prefix="/api")         # 搜索
app.include_router(graph_router, prefix="/api")          # 知识图谱
app.include_router(categories_router, prefix="/api")     # 分类
app.include_router(contents_router, prefix="/api")       # 内容
app.include_router(skills_router, prefix="/api")         # Skills
app.include_router(prompts_router, prefix="/api")        # Prompts
app.include_router(import_router, prefix="/api")        # 导入
app.include_router(agent_router, prefix="/api")         # Agent（M1，SSE ReAct）
```

### 8.2 核心API接口

#### 笔记接口 - [notes.py](file:///d:/知枢星图/backend/app/api/routes/notes.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notes` | 获取笔记列表 |
| POST | `/notes` | 创建笔记 |
| GET | `/notes/:id` | 获取笔记详情 |
| PUT | `/notes/:id` | 更新笔记 |
| DELETE | `/notes/:id` | 删除笔记 |
| GET | `/notes/:id/backlinks` | 获取反向链接 |

**双向链接解析**：
```python
# 使用 [[笔记标题]] 语法
LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

def parse_links(content: str) -> list:
    """提取笔记中的双向链接"""
    matches = LINK_PATTERN.findall(content)
    return [title.strip() for title in matches]
```

#### 搜索接口 - [search.py](file:///d:/知枢星图/backend/app/api/routes/search.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search` | 全文搜索 |
| POST | `/search/ai` | AI智能问答 |
| POST | `/search/chat` | AI对话 |
| GET | `/search/vector` | 向量检索 |
| POST | `/search/vector/batch` | 批量向量检索 |
| POST | `/search/vector/rebuild` | 重建向量索引 |
| GET | `/search/hybrid` | 混合检索 |
| GET | `/search/bm25` | BM25检索 |
| POST | `/search/chat/stream` | SSE对话流 |
| POST | `/search/ai/stream` | SSE搜索流 |

#### 知识图谱接口 - [graph.py](file:///d:/知枢星图/backend/app/api/routes/graph.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/graph/global` | 全局图谱 |
| GET | `/graph/local/:id` | 局部图谱 |

**图谱数据结构**：
```python
class GraphNode:
    id: str
    label: str
    type: str  # folder/note/tag
    color: str
    size: int

class GraphEdge:
    source: str
    target: str
    type: str  # contains/has_tag/links_to
```

#### Skills接口 - [skills.py](file:///d:/知枢星图/backend/app/api/routes/skills.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/skills` | 获取Skills列表 |
| POST | `/skills` | 创建Skill |
| POST | `/skills/:id/execute` | 执行Skill |
| GET | `/skills/:id/executions` | 执行历史 |

#### Agent接口 - [agent.py](file:///d:/知枢星图/backend/app/api/routes/agent.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent/chat/stream` | Agent ReAct 问答（SSE 事件：thought/action/observation/check/final_answer + [DONE]；异常降级旧 /search/ai） |
| GET | `/agent/sessions` | 获取会话列表 |
| POST | `/agent/sessions` | 新建会话 |

---

## 9. 依赖关系

### 9.1 Python依赖

```
# Web框架
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# 数据库
sqlalchemy>=2.0.0
pydantic>=2.10.0

# 认证
python-jose[cryptography]>=3.3.0
bcrypt>=4.0.0

# 向量处理
faiss-cpu>=1.9.0
sentence-transformers>=3.0.0

# RAG框架
langchain>=0.3.0
langchain-core>=0.3.29
langchain-openai>=0.2.0
langchain-community>=0.3.0

# Agent 图编排（锁 0.2.x，兼容 langchain-core<1.0；checkpoint 锁 2.x 配套）
langgraph>=0.2.50,<0.3.0
langgraph-checkpoint==2.1.2
langgraph-checkpoint-sqlite>=2,<3

# LLM服务
openai>=1.50.0
dashscope>=1.20.0

# 可观测（M2，fail-silent；2.x 与 langchain 0.3 不兼容，用 4.x）
langfuse>=4,<5

# 搜索
rank_bm25>=0.2.2
jieba>=0.42.1

# 速率限制
slowapi>=0.1.9

# 媒体处理
faster-whisper>=0.10.0
yt-dlp>=2024.0.0
```

### 9.2 NPM依赖

```json
{
  "dependencies": {
    "vue": "^3.4.21",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "naive-ui": "^2.38.1",
    "axios": "^1.6.7",
    "d3": "^7.9.0",
    "markdown-it": "^14.0.0"
  },
  "devDependencies": {
    "vite": "^5.1.4",
    "typescript": "^5.3.3",
    "tailwindcss": "^3.4.1",
    "vue-tsc": "^2.0.6"
  }
}
```

### 9.3 模块依赖图

```
┌─────────────────────────────────────────────────────────────┐
│                        Routes Layer                          │
│  notes.py | search.py | graph.py | skills.py | auth.py      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Services Layer                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │Vector Store  │ │ BM25 Service │ │Embedding Svc│          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │Hybrid Search │ │ RAG Chain    │ │ Stream Svc   │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Models Layer                            │
│  Note | Folder | Category | Tag | User | Skill              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DB Layer                               │
│  SQLAlchemy + SQLite + FAISS Index                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. 运行方式

### 10.1 环境要求

- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 10.2 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动服务
python -m uvicorn app.main:app --reload --port 8000

# 或使用启动脚本
./start.bat  # Windows
./start.sh   # Linux/Mac
```

### 10.3 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 生产构建
npm run build
```

### 10.4 访问应用

- 前端：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 10.5 环境变量配置

```env
# 阿里云 DashScope API（用于文本向量化）
DASHSCOPE_API_KEY=your_api_key_here

# JWT 密钥
JWT_SECRET_KEY=your_secret_key_here

# LLM 模型配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=qwen-turbo

# 数据库
DATABASE_URL=sqlite:///./data/knowledge.db

# FAISS 索引路径
FAISS_INDEX_PATH=/tmp/zhishuxingtu_faiss

# 混合检索配置
USE_HYBRID_SEARCH=true
VECTOR_WEIGHT=0.6
BM25_WEIGHT=0.4
```

---

## 附录

### A. 版本演进

```
V1 MVP          V2 分类升级       V3 Skill         V4 扩展
  │                │                │                │
  ▼                ▼                ▼                ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 笔记管理 │    │ 分类体系 │    │ Skill   │    │ 语义搜索 │
│ 文件夹   │ -> │ 内容类型 │ -> │ 执行引擎 │ -> │ 导入导出 │
│ 标签     │    │ 素材管理 │    │ AI生成  │    │ 浏览器插件│
│ 双向链接 │    │ 模板系统 │    │ 自动化  │    │ 批量处理 │
│ 知识图谱 │    │          │    │         │    │         │
│ AI问答   │    │          │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### B. 关键配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_CHUNK_SIZE` | 800 | 文本块最大字符数 |
| `OVERLAP_RATIO` | 0.5 | 相邻块重叠比例 |
| `USE_HYBRID_SEARCH` | true | 启用混合检索 |
| `VECTOR_WEIGHT` | 0.6 | 向量检索权重 |
| `BM25_WEIGHT` | 0.4 | BM25权重 |
| `USE_RERANKER` | true | 启用Reranker |
| `RERANKER_TOP_K` | 5 | Reranker返回数量 |

### C. 许可

MIT License

---

*文档生成时间：2026-05-06*
