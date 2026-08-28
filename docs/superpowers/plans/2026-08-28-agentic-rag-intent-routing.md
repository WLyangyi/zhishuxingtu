# Agentic RAG 意图识别（Intent Routing）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Agentic RAG 的 LangGraph 图开头加入「意图识别」节点，将问题按 4 类意图（knowledge / direct_answer / web_search / note_write）路由到不同处理分支，修复 M2 评估发现的「简单题 agent 掉链」问题并降低无谓 token 消耗。

**Architecture:** 借鉴 GitHub 主流 agentic RAG 实现（LangChain 官方 router-knowledge-base、JEONGHEESIK/LangGraph-Agentic-Graph-RAG、sotaaz Query Routing）的统一模式：**图入口加一个 LLM 结构化输出（Pydantic + Literal）分类节点 → 条件边按意图路由**。knowledge/web_search/note_write 三条意图复用现有 `agent_step` ReAct 循环（通过注入 system prompt 提示引导），仅 `direct_answer` 走新增短路节点直答，绕过工具循环与三查。分类失败 fail-safe 默认 `knowledge`（绝不阻塞主流程）。

**Tech Stack:** Python 3.11 / FastAPI / LangGraph 0.2.x / DeepSeek V4 (function_calling 结构化输出) / Vue 3 / Naive UI / pytest

---

## 背景与依据

- 升级笔记 M2 实测（[升级笔记.md](file:///d:/知枢星图/docs/agentic-rag-upgrade/升级笔记.md)）：agent 在 q017/q018/q025 等简单题上发挥不稳定，「单轮检索就够的场景反而掉链」——根因是**所有问题都跑完整 ReAct + 三查**。
- 业界参考（调研结论）：
  - LangChain 官方 router：`classify_query` 用 Pydantic 保证输出合法，按来源路由。
  - sotaaz Query Routing：`requires_retrieval` 标志决定跳过检索，是本方案 `direct_answer` 短路的理论来源。
  - JEONGHEESIK Graph-RAG：`knowledge / calculation / database / api_call / code_exec` 五类意图路由 + 质量门控。

## 方案要点

1. **4 类意图**（对齐本项目已有能力：7 工具 + 三查 + HITL + Tavily）：
   - `knowledge`：知识库检索 → 现有 ReAct + 三查（默认，最保守）
   - `direct_answer`：通用常识/闲聊 → 新增直答节点，跳过检索与三查，省 token
   - `web_search`：实时/外部信息 → 进 ReAct，但注入提示优先调 Tavily
   - `note_write`：写入笔记 → 进 ReAct，注入提示引导调 create_note（复用 HITL 审批）
2. **图结构**：`START → intent_classify →(条件边)→ agent_step | direct_answer → output → END`
3. **fail-safe**：分类异常/非法输出一律回退 `knowledge`，主流程不受阻。
4. **可观测**：新增 `intent` 类型 thought 事件，前端时间线展示「意图识别」节点；eval 报告新增意图分布与工具调用数。

---

## 文件结构

| 文件 | 改动 | 职责 |
|---|---|---|
| `backend/app/services/agent/prompts.py` | 修改 | 新增 `QueryIntent` 模型、`INTENT_CLASSIFY_PROMPT`、`DIRECT_ANSWER_PROMPT`、`INTENT_HINTS` |
| `backend/app/services/agent/state.py` | 修改 | state 增加 `intent: str` 字段 |
| `backend/app/services/agent/nodes.py` | 修改 | 新增 `intent_classify` / `direct_answer` / `route_intent`；`agent_step` 注入意图提示 |
| `backend/app/services/agent/graph.py` | 修改 | 图接入 `intent_classify` 起始节点 + 条件边 |
| `backend/eval/run_eval.py` | 修改 | 采集意图分布 + 工具调用数，报告输出 |
| `backend/scripts/verify_agent_graph.py` | 修改 | 运行后打印识别到的意图 |
| `backend/tests/test_agent_intent.py` | 新建 | 意图路由单元测试 |
| `frontend/src/api/agent.ts` | 修改 | `TimelineEvent.type` 增加 `'intent'` |
| `frontend/src/views/AIAssistant.vue` | 修改 | SSE 事件处理接受 `'intent'` 类型 |
| `frontend/src/components/agent/AgentTimeline.vue` | 修改 | `intent` 事件图标 + 标签 + 颜色 |
| `docs/agentic-rag-upgrade/升级笔记.md` | 修改 | 追加 M6 进展（意图识别） |

---

## Task 1: prompts.py 新增意图识别相关提示词与模型

**Files:**
- Modify: `backend/app/services/agent/prompts.py:1`（import 行）与文件末尾追加

- [ ] **Step 1: 修改 import 行**

```python
from typing import Literal

from pydantic import BaseModel, Field
```

- [ ] **Step 2: 文件末尾追加以下内容**

```python
# ---------- 意图识别 ----------
class QueryIntent(BaseModel):
    intent: Literal["knowledge", "direct_answer", "web_search", "note_write"] = Field(
        description="问题意图分类"
    )
    reason: str = Field(description="分类理由,一句话")


INTENT_CLASSIFY_PROMPT = """你是查询意图识别器。把用户问题归类到以下四类之一:
- knowledge: 需要检索个人知识库笔记来回答(含个人资料、项目细节、笔记中的具体内容、多跳/对比分析)
- direct_answer: 通用常识、概念解释、闲聊寒暄,不依赖个人知识库即可回答
- web_search: 需要实时/外部最新信息(新闻、股价、天气、技术动态等)
- note_write: 用户明确想把某段内容记录/保存到知识库

判断规则:
- 不确定时默认 knowledge(宁可多检索,不可漏答知识库内容)。
- 提到具体笔记、个人经历、项目、简历等个性化内容,一律 knowledge。
- 只有明确的通用知识/闲聊才选 direct_answer。

只输出结构化结果 intent + reason。"""

DIRECT_ANSWER_PROMPT = """你是「知枢星图」的智能助手。这条问题无需检索知识库,请直接回答。

要求:
- 用中文回答,简洁清晰。
- 若问题可能是关于用户个人知识库里的特定内容(如个人笔记、私人资料),不要编造,说明"该内容可能存在于用户的知识库中,如需准确信息建议检索知识库"。
- 通用知识/闲聊正常回答即可。"""

INTENT_HINTS = {
    "web_search": (
        "## 本次意图:实时/外部信息\n"
        "用户问题需要实时或知识库之外的信息,请优先调用 web_search 工具获取最新内容;\n"
        "若 web_search 不可用或没有结果,再回退到知识库检索。"
    ),
    "note_write": (
        "## 本次意图:写入笔记\n"
        "用户想把内容记录到知识库,请调用 create_note 工具创建笔记(该操作会请求用户审批)。\n"
        "从用户的话里提取清晰的标题(title)与正文(content),必要时可先检索知识库确认是否已有重复内容。"
    ),
}
```

- [ ] **Step 3: 验证导入无语法错误**

Run: `cd backend; .venv\Scripts\python.exe -c "from app.services.agent import prompts; print('ok', prompts.QueryIntent.__annotations__)"`
Expected: `ok {'intent': typing.Literal['knowledge', 'direct_answer', 'web_search', 'note_write'], 'reason': <class 'str'>}`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent/prompts.py
git commit -m "feat(agent): add intent classification prompt and schema"
```

---

## Task 2: state.py 增加 intent 字段

**Files:**
- Modify: `backend/app/services/agent/state.py:22`

- [ ] **Step 1: 追加字段**

```python
    intent: str
```

（加到 `answer_ok: str` 之后）

- [ ] **Step 2: 验证**

Run: `cd backend; .venv\Scripts\python.exe -c "from app.services.agent.state import AgentState; assert 'intent' in AgentState.__annotations__; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/agent/state.py
git commit -m "feat(agent): add intent field to AgentState"
```

---

## Task 3: nodes.py 新增意图节点 + agent_step 提示注入

**Files:**
- Modify: `backend/app/services/agent/nodes.py:17-25`（import）与 `:93-126`（agent_step）与文件末尾（新节点）

- [ ] **Step 1: 扩展 prompts import**

把现有 `from app.services.agent.prompts import (...)` 改为：

```python
from app.services.agent.prompts import (
    DIRECT_ANSWER_PROMPT,
    GRADE_ANSWER_PROMPT,
    GRADE_DOCUMENTS_PROMPT,
    GRADE_HALLUCINATIONS_PROMPT,
    INTENT_CLASSIFY_PROMPT,
    INTENT_HINTS,
    REACT_SYSTEM_PROMPT,
    GradeAnswer,
    GradeDocuments,
    GradeHallucinations,
    QueryIntent,
)
```

- [ ] **Step 2: agent_step 注入意图提示**

在 `agent_step` 中 `system_prompt = REACT_SYSTEM_PROMPT` 之后插入：

```python
    hint = INTENT_HINTS.get(state.get("intent") or "")
    if hint:
        system_prompt += "\n\n" + hint
```

- [ ] **Step 3: 文件末尾（`route_answer_quality` 之后）追加新节点与路由**

```python
# ---------- 意图识别 ----------
def intent_classify(state: AgentState) -> Dict[str, Any]:
    """意图识别节点。分类失败时 fail-safe 默认 knowledge，不让主流程被阻塞。"""
    question = state.get("question") or ""
    intent = "knowledge"
    reason = "fail-safe 默认走知识库检索"
    try:
        provider = get_deepseek_provider()
        structured = provider.with_structured_output(QueryIntent)
        resp = structured.invoke(
            [
                SystemMessage(content=INTENT_CLASSIFY_PROMPT),
                HumanMessage(content=question),
            ]
        )
        candidate = (getattr(resp, "intent", "") or "").strip().lower()
        if candidate in ("knowledge", "direct_answer", "web_search", "note_write"):
            intent = candidate
            reason = (getattr(resp, "reason", "") or "")[:120]
        else:
            reason = f"模型返回非法意图 {candidate!r},默认 knowledge"
    except Exception as exc:  # noqa: BLE001 分类只是路由提示,失败不阻断
        reason = f"分类失败,默认 knowledge: {exc}"
    return {
        "intent": intent,
        "thoughts": _append_thought(state, {"type": "intent", "content": f"意图识别: {intent} | {reason}"}),
    }


def direct_answer(state: AgentState, *, store: BaseStore = None) -> Dict[str, Any]:
    """直答分支:通用常识/闲聊,跳过工具循环与三查,省 token 且避免简单题掉链。"""
    provider = get_deepseek_provider()
    system_prompt = DIRECT_ANSWER_PROMPT
    preference_context = get_preference_context(state.get("user_id", ""), store)
    if preference_context:
        system_prompt += "\n\n## 用户长期偏好\n" f"{preference_context}"
    question = state.get("question") or ""
    resp = provider.get_chat_model().invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
    )
    answer = (resp.content or "").strip() or "抱歉,我暂时无法回答这个问题。"
    return {
        # 同步写入 checkpoint,保证多轮会话上下文连续
        "messages": [HumanMessage(content=question), AIMessage(content=answer)],
        "answer": answer,
        "thoughts": _append_thought(
            state, {"type": "thought", "content": "direct_answer: 通用知识/闲聊,跳过检索直接作答"}
        ),
    }


def route_intent(state: AgentState) -> str:
    """条件边:按意图返回下一节点。direct_answer 走直答,其余走 agent_step。"""
    return "direct_answer" if (state.get("intent") == "direct_answer") else "agent_step"
```

注意：`BaseStore` 已在 nodes.py 顶部 import（`from langgraph.store.base import BaseStore`），`HumanMessage/AIMessage` 已 import，无需新增。

- [ ] **Step 4: 验证模块导入**

Run: `cd backend; .venv\Scripts\python.exe -c "from app.services.agent import nodes; print('ok', hasattr(nodes,'intent_classify'), hasattr(nodes,'direct_answer'), hasattr(nodes,'route_intent'))"`
Expected: `ok True True True`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/nodes.py
git commit -m "feat(agent): add intent_classify/direct_answer nodes and route_intent edge"
```

---

## Task 4: graph.py 接入意图路由

**Files:**
- Modify: `backend/app/services/agent/graph.py:10-23`（import）与 `:41`（START 边）

- [ ] **Step 1: 扩展 nodes import**

把 `from app.services.agent.nodes import (...)` 改为加入：

```python
    direct_answer,
    intent_classify,
    route_intent,
```

（按字母序插入）

- [ ] **Step 2: build_graph 中把 `g.add_edge(START, "agent_step")` 替换为**

```python
    g.add_node("intent_classify", intent_classify)
    g.add_node("direct_answer", direct_answer)
    g.add_edge(START, "intent_classify")
    g.add_conditional_edges(
        "intent_classify",
        route_intent,
        {"agent_step": "agent_step", "direct_answer": "direct_answer"},
    )
    g.add_edge("direct_answer", "output")
```

- [ ] **Step 3: 验证图编译 + 全量回归**

Run: `cd backend; .venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 全部通过（现有 test_agent_m4_m5.py 等 6+ 用例不回归）

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent/graph.py
git commit -m "feat(agent): wire intent classifier as graph entry with conditional routing"
```

---

## Task 5: run_eval.py 采集意图分布与工具调用数

**Files:**
- Modify: `backend/eval/run_eval.py:1`（import）`:53-78`（run_agent）`:236-246`（main 调用）`:116-158`（write_report）

- [ ] **Step 1: 文件顶部加 import**

```python
from collections import Counter
```

- [ ] **Step 2: 重写 run_agent（返回意图 + 工具调用数）**

```python
def run_agent(question: str, user_id: str):
    """新链路: graph.stream, 收集 final answer + 检索到的 documents + 意图 + 工具调用数。"""
    from app.services.agent.graph import build_input, get_graph
    from app.services.observability.langfuse_trace import build_stream_config
    from app.services.tools.context import ToolContext, set_tool_context

    set_tool_context(ToolContext(user_id=user_id, session_id="eval-sess"))
    graph = get_graph()
    thread_id = f"eval-{int(time.time() * 1000)}"
    input_data = build_input(question, session_id="eval-sess", user_id=user_id)

    final_answer = ""
    documents: List[dict] = []
    tool_calls = 0
    seen: set = set()
    for step in graph.stream(input_data, config=build_stream_config(thread_id)):
        for _, v in step.items():
            if v.get("answer"):
                final_answer = v["answer"]
            tool_calls = max(tool_calls, len(v.get("tool_calls_log") or []))
            for d in v.get("documents") or []:
                did = d.get("id")
                if did and did not in seen:
                    seen.add(did)
                    documents.append(d)

    config = {"configurable": {"thread_id": thread_id}}
    intent = (graph.get_state(config).values or {}).get("intent") or "knowledge"
    retrieved_ids = [d["id"] for d in documents]
    return retrieved_ids, final_answer or "", documents, intent, tool_calls
```

- [ ] **Step 3: main() 中更新调用与 agent 行**

把 `a_ids, a_answer, a_sources = run_agent(question, uid)` 改为：

```python
            a_ids, a_answer, a_sources, a_intent, a_tool_calls = run_agent(question, uid)
```

把 agent 行改为：

```python
                "agent": {
                    "recall": recall_at_k(a_ids, rel_ids, TOP_K),
                    "retrieved": a_ids,
                    "intent": a_intent,
                    "tool_calls": a_tool_calls,
                },
```

- [ ] **Step 4: write_report 增加意图分布与平均工具调用**

在「按分类分桶」段落之后追加：

```python
    lines += [
        "",
        "## Agent 意图分布与成本",
        "",
        f"- 意图分布: {dict(Counter(r['agent'].get('intent') for r in results))}",
        f"- agent 平均工具调用次数: {mean([r['agent'].get('tool_calls') or 0 for r in results]):.2f}",
        "",
    ]
```

（`mean` 已在文件顶部 import）

- [ ] **Step 5: 验证 eval 脚本可运行（先 --limit 2 --skip-judge 冒烟）**

Run: `cd backend; .venv\Scripts\python.exe eval/run_eval.py --limit 2 --skip-judge`
Expected: 正常输出 q001/q002 两行，报告写入 `eval/reports/2026-08-28-comparison.md`，包含「Agent 意图分布与成本」段

- [ ] **Step 6: Commit**

```bash
git add backend/eval/run_eval.py
git commit -m "feat(eval): collect intent distribution and tool call counts"
```

---

## Task 6: verify_agent_graph.py 打印意图

**Files:**
- Modify: `backend/scripts/verify_agent_graph.py:54-64`

- [ ] **Step 1: stream 循环结束后、打印最终答案前追加**

```python
    final_values = graph.get_state({"configurable": {"thread_id": thread_id}}).values or {}
    print(f"[意图] {final_values.get('intent', 'knowledge')}\n")
```

- [ ] **Step 2: 验证**

Run: `cd backend; .venv\Scripts\python.exe scripts/verify_agent_graph.py`
Expected: 输出中新增 `[意图] knowledge`（多跳问题应被归为 knowledge）

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_agent_graph.py
git commit -m "feat(agent): print detected intent in verify script"
```

---

## Task 7: 前端时间线支持 intent 事件

**Files:**
- Modify: `frontend/src/api/agent.ts:33`
- Modify: `frontend/src/views/AIAssistant.vue:260`
- Modify: `frontend/src/components/agent/AgentTimeline.vue`

- [ ] **Step 1: agent.ts 类型联合加入 'intent'**

```typescript
  type: 'thought' | 'action' | 'observation' | 'check' | 'tool' | 'intent'
```

- [ ] **Step 2: AIAssistant.vue SSE 处理接受 intent**

```typescript
  if (['thought', 'action', 'observation', 'check', 'intent'].includes(message.type)) {
```

- [ ] **Step 3: AgentTimeline.vue 增加图标与标签**

import 行改为：

```vue
import { Brain, Compass, Eye, Play, ShieldCheck, Wrench } from 'lucide-vue-next'
```

图标（`<ShieldCheck v-else-if="event.type === 'check'" />` 之后）：

```vue
        <Compass v-else-if="event.type === 'intent'" :size="14" />
```

label 映射（`check: '质量检查'` 之后）：

```ts
    intent: '意图识别'
```

颜色（`&.check { color: var(--primary-color); }` 之后）：

```scss
  &.intent { color: var(--accent-purple); }
```

- [ ] **Step 4: 前端构建验证**

Run: `cd frontend; npm run build`
Expected: `vue-tsc` 0 错误 + `vite build` 成功

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/agent.ts frontend/src/views/AIAssistant.vue frontend/src/components/agent/AgentTimeline.vue
git commit -m "feat(frontend): show intent classification in agent timeline"
```

---

## Task 8: 新增意图路由单元测试

**Files:**
- Create: `backend/tests/test_agent_intent.py`

- [ ] **Step 1: 写测试文件（全部 mock，不触发真实 LLM）**

```python
# -*- coding: utf-8 -*-
from app.services.agent.nodes import direct_answer, intent_classify, route_intent


def _state(**kw):
    base = {"question": "测试", "intent": "", "thoughts": [], "user_id": "u1", "session_id": "s1"}
    base.update(kw)
    return base


def test_route_intent_direct_answer_goes_to_direct_answer():
    assert route_intent({"intent": "direct_answer"}) == "direct_answer"


def test_route_intent_others_go_to_agent_step():
    assert route_intent({}) == "agent_step"
    assert route_intent({"intent": "knowledge"}) == "agent_step"
    assert route_intent({"intent": "web_search"}) == "agent_step"
    assert route_intent({"intent": "note_write"}) == "agent_step"


def test_intent_classify_sets_intent(monkeypatch):
    class FakeResp:
        intent = "web_search"
        reason = "需要实时信息"

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state(question="今天有什么AI新闻"))
    assert out["intent"] == "web_search"
    assert out["thoughts"][0]["type"] == "intent"


def test_intent_classify_fails_safe_to_knowledge(monkeypatch):
    class FakeProvider:
        def with_structured_output(self, model):
            raise RuntimeError("llm down")

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state())
    assert out["intent"] == "knowledge"


def test_intent_classify_rejects_invalid_intent(monkeypatch):
    class FakeResp:
        intent = "hacker"
        reason = "bad"

    class FakeStructured:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def with_structured_output(self, model):
            return FakeStructured()

    monkeypatch.setitem(intent_classify.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    out = intent_classify(_state())
    assert out["intent"] == "knowledge"


def test_direct_answer_returns_answer_and_writes_checkpoint(monkeypatch):
    class FakeResp:
        content = "你好!有什么可以帮你?"

    class FakeChat:
        def invoke(self, msgs):
            return FakeResp()

    class FakeProvider:
        def get_chat_model(self):
            return FakeChat()

    monkeypatch.setitem(direct_answer.__globals__, "get_deepseek_provider", lambda: FakeProvider())
    monkeypatch.setitem(
        direct_answer.__globals__, "get_preference_context", lambda *a, **k: ""
    )
    out = direct_answer(_state(question="你好"))
    assert out["answer"] == "你好!有什么可以帮你?"
    assert out["messages"][0].content == "你好"
    assert out["messages"][1].content == "你好!有什么可以帮你?"
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd backend; .venv\Scripts\python.exe -m pytest tests/test_agent_intent.py -v`
Expected: 6 passed

- [ ] **Step 3: 全量回归**

Run: `cd backend; .venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_agent_intent.py
git commit -m "test(agent): cover intent routing, fail-safe and direct answer"
```

---

## Task 9: 运行真实链路验证（手动冒烟）

**Files:**
- 无代码改动，纯验证

- [ ] **Step 1: 验证多跳知识问题走 knowledge**

Run: `cd backend; .venv\Scripts\python.exe scripts/verify_agent_graph.py --question "5月10日有哪些科技产品发布?"`
Expected: `[意图] knowledge`，SSE 链路完整，三查正常

- [ ] **Step 2: 验证闲聊走 direct_answer**

Run: `cd backend; .venv\Scripts\python.exe scripts/verify_agent_graph.py --question "你好,介绍一下你自己"`
Expected: `[意图] direct_answer`，直接出答案、无工具调用

- [ ] **Step 3: 验证实时信息走 web_search**

Run: `cd backend; .venv\Scripts\python.exe scripts/verify_agent_graph.py --question "今天AI行业有什么最新动态?"`
Expected: `[意图] web_search`（无 Tavily key 时 web_search 返回"未启用"，agent 优雅降级）

- [ ] **Step 4: 验证写笔记走 note_write + HITL**

通过前端 `/api/agent/chat/stream` 发「帮我把 xxx 记到知识库」，预期出现 `approval_required` 审批卡，拒绝/批准均正常（复用现有 HITL 链路，不新增代码）

---

## Task 10: 跑 eval 对比 + 更新升级笔记

**Files:**
- Modify: `docs/agentic-rag-upgrade/升级笔记.md`

- [ ] **Step 1: 跑全量 eval**

Run: `cd backend; .venv\Scripts\python.exe eval/run_eval.py`
Expected: 50 条跑完，报告写入 `eval/reports/2026-08-28-comparison.md`

- [ ] **Step 2: 读取报告关键数字**

Read: `backend/eval/reports/2026-08-28-comparison.md`
重点核对：recall / faithfulness / relevancy 总体与分桶；**意图分布**（应 50 条全为 knowledge，证明分类器不漏判知识库问题）；**平均工具调用数**。

- [ ] **Step 3: 升级笔记追加 M6 进展**

在 `## 六、进展日志` 顶部（最新在前）追加一段，格式参照既有条目，包含：方案来源（GitHub 参考）、4 类意图、图结构、fail-safe、eval 结果对比（与 M2 历史数据 0.993/0.983、0.962/0.891、1.000/0.936 对照）、前端时间线、新增测试数。

- [ ] **Step 4: Commit**

```bash
git add docs/agentic-rag-upgrade/升级笔记.md
git commit -m "docs: record M6 intent routing milestone"
```

---

## 自检结果

- **Spec 覆盖**：4 类意图 ✓（Task 1 定义 + Task 3/4 节点与路由）；eval 验证 ✓（Task 5/10）；前端可见 ✓（Task 7）；fail-safe ✓（Task 3 + Task 8 测试）。
- **占位符**：无 TBD/TODO，所有代码步骤含完整实现。
- **类型一致**：`intent` 字段在 state.py（Task 2）→ nodes.py（Task 3）→ graph.py（Task 4）→ run_eval.py（Task 5）全程同名；`route_intent` 返回 `"agent_step" | "direct_answer"` 与 graph 条件边 mapping key 一致（Task 4 Step 2）；前端 `'intent'` 类型在 agent.ts / AIAssistant.vue / AgentTimeline.vue 三处一致。
- **已知边界**：若分类器把知识库问题误判为 `direct_answer`，eval 中该行 recall=0、faithfulness≈0 —— 会显式暴露在报告意图分布里，便于人工校准 prompt（符合项目「抽 10 条人工校准」惯例）。
