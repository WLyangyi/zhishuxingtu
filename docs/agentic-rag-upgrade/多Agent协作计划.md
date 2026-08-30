# 知枢星图 · M7 多 Agent 协作升级计划（可行性评估稿）

> **状态**：已评审拍板（2026-08-30）；同日深度评审修订 **v2**——新增 A′ 平铺图实现形式、修正 §五风险表、补齐验收体系（意图标注 / 容差带 / 测试回归 / 回退开关），见 §四/§五/§六/§八
> **前置阅读**：`升级笔记.md`（D1-D13 架构决策）、`实施计划.md`（M0-M6）
> **已落地**：实施清单已并入 `实施计划.md` 作为 M7；架构决策已记入 `升级笔记.md` D13

---

## 一、目标与一句话结论

**目标**：把现有「单 ReAct Agent + 意图提示」升级为「编排器自动识别意图 → 路由到专业子 Agent」的多 Agent 协作架构。

**可行性结论：可行，且有低风险演进路径。** 现有 `intent_classify` 节点本质上已经是编排器雏形（LLM 结构化输出四分类 + fail-safe），升级的核心工作是把它从「两分支路由」扩成「多子 Agent 路由」，并把现有主图整体降级为一个子 Agent（knowledge_agent）。不需要推翻重来，不需要引入新框架。

**诚实的收益/成本账**（个人知识库场景）：

| 收益 | 成本 |
|---|---|
| 工具集瘦身：每个子 Agent 只看相关工具，减少误调用（现在 7 个工具全量绑定） | 编排错误的影响面变大（分类错 → 进错 agent），依赖 fail-safe 兜底 |
| 提示词专业化：子 Agent system prompt 更短更准，ReAct 决策质量提升 | 子图流式/HITL 中断冒泡需 P0 验证（见 §五） |
| 混合意图可编排（方案 B）："搜网络并保存成笔记"能拆成两步 | 简单问题 token/延迟上升（可用预算分层控制） |
| 秋招叙事：Supervisor 模式 + eval 新旧对比量化收益，面试硬通货 | DeepSeek 单 provider，"多 Agent"是同模型多角色，无模型多样性收益（如实说明） |

---

## 二、三个候选方案

### 方案 A：静态编排器（一次性路由 + 专业子 Agent）—— 推荐起步

```
START → intent_classify(编排器) ──┬─ chat_agent        （现有 direct_answer，零改动）
                                 ├─ knowledge_agent   （现有主链专业化，实现形式见 §四，带三查）
                                 ├─ web_research_agent（新拆，web_search 专职）
                                 └─ note_write_agent  （新拆，create_note + HITL 专职）
       → output → END
```

- 编排成本为零：复用现有 `intent_classify` 那一次 LLM 调用（`nodes.py:442`），只扩 schema 不加调用。
- 每个问题只走一个子 Agent，行为可预期、好调试、好评测。
- 局限：混合意图（"先搜网络再写成笔记"）只能命中一个 agent。

### 方案 B：Supervisor 循环编排（编排器可多轮派单）

- 编排器是独立 LLM 节点：每轮决定「派给哪个子 Agent / 直接作答 / 结束」，子 Agent 返回结果摘要，编排器可继续派单。
- 能处理混合意图：web_research_agent 干完 → 编排器看结果 → 再派 note_write_agent。
- 成本：每次派单多 1 次编排 LLM 调用；需要编排轮次上限（建议 ≤3）防循环。
- 实现方式：手写 supervisor 节点 + 条件边（符合 D1「纯 LangGraph 不叠加」；**不引** `langgraph-supervisor` 库，0.2.x 手写即可）。

### 方案 C：Network / Swarm 自由转交 —— 不推荐

Agent 间互相 handoff 无中心编排，调试困难、token 不可控、面试也讲不清边界。个人场景过度设计，明确排除。

### 推荐路径

**A 起步（M7.1-M7.4），用 50 条 eval 集验证有收益后再决定是否局部升级 B（M7.5 可选）。** 理由：个人知识库绝大多数请求是单一意图，A 零额外编排成本；B 的增量价值集中在混合意图，可以作为独立里程碑按需启动。

---

## 三、目标架构

### 3.1 子 Agent 划分与工具分配

| 子 Agent | 工具 | 三查 | 说明 |
|---|---|---|---|
| chat_agent | 无 | 无 | 现有 `direct_answer` 节点原封不动 |
| knowledge_agent | search_notes, get_note, get_graph_neighbors, list_tags, list_folders, **web_search** | 全三查保留 | 现有主链专业化（实现形式见 §四）；`create_note` 移出（HITL 专职化）；**web_search 保留作回退**——意图误判为 knowledge 但实需联网时 agent 仍有出路，现有 INTENT_HINTS 回退逻辑不变；prompt 加「保存类请求告知用户单独发起」，防混合意图被静默吞掉 |
| web_research_agent | web_search, search_notes | 仅幻觉查（hallucination_check），**无 answer_quality** | 信源引用进答案；web_search 结果并入 documents 证据池的既有机制复用；砍 answer_quality 是明示取舍（跑题风险由 prompt 约束），记入 §七 |
| note_write_agent | create_note, search_notes | 无（人工审批即质量关） | search_notes 用于写入前查重；`interrupt` HITL 只在此子图出现，缩小中断语义范围 |

> 不拆 graph_analysis_agent：图谱工具只有 `get_graph_neighbors` 一个，专职化收益低于子图维护成本（YAGNI）。

### 3.2 状态共享（关键设计）

- 顶层 `AgentState`（`state.py`）保持不变，作为编排器与子 Agent 之间的总线；两种实现形式下子 Agent 与顶层共享同一 schema（A′ 天然共享；A-子图同 schema 注册，无映射成本）。
- 新增可选字段（均 `total=False`，旧 checkpoint 兼容）：`current_agent`（A′ 形式的路由载体）、`turn_start_index`（修复 `_best_answer` 跨轮污染，见 §五 #6）。
- `documents` 证据池继续全局共享：knowledge/web_research 的检索结果、`get_note` 完整内容、联网结果都进池（病灶 A/P18 的教训直接沿用）。
- `thoughts` / `tool_calls_log` 由子 Agent 追加，前端时间线事件源不变。

### 3.3 预算与熔断分层

| 层级 | 现状 | 升级后 |
|---|---|---|
| 全局 token 预算 | `TOKEN_BUDGET=10000`（`config.py:6`） | 保留为总闸，编排层检查 |
| 子 Agent 迭代上限 | `MAX_ITERATIONS=8` 单值 | 按 agent 差异化：knowledge 8、web_research 5、note_write 3；实现：`should_continue` 按 `current_agent` 查表（A′）或子图各自 config（A-子图）。注意 `iteration` 是共享字段，方案 B 多次派单时必须派单级重置 + 派单计数器，否则上限失效 |
| 重复检索熔断 | `searched_queries` 同轮去重（`nodes.py:210-231`） | 保持，粒度为子 Agent 内部 |
| 工具永久熔断 | web_search 未配置短路（`nodes.py:233-244`） | 保持，tool_log 全局可见 |
| 编排轮次 | 不存在 | 方案 B 时 ≤3 轮；方案 A 天然 1 轮 |
| fail-safe | 分类失败默认 knowledge | 保持，knowledge_agent 是全能回退位 |

---

## 四、实现形式：A-子图 vs A′ 平铺图（评审 v2 重写，M7.0 双骨架对比后定稿）

方案 A 的外部行为（编排器路由 → 4 个专业 agent）有**两种实现形式，风险差异巨大**：

### 形式一 A-子图（原方案）：编译子图作父图节点

现有整张图（`graph.py:33-77` 的 10 节点）整体降级为 knowledge 子图：

1. 把 `build_graph()` 拆出「主链子图构建函数」（agent_step → execute_tool → grade_documents → generate → 三查 → output，入口去 `intent_classify`）。
2. 顶层新图：START → 编排器 → 条件边 → {chat_agent, knowledge 子图, web_research 子图, note_write 子图} → output → END。
3. LangGraph 0.2.x 原生支持「编译后的图作为父图节点」（`add_node("knowledge_agent", compiled_subgraph)`），共享 state key 自动合并。
4. `checkpointer`（SqliteSaver）与 `store`（偏好记忆）挂顶层图，子图自动继承。

- **代价（评审确认是「必然」而非「可能」）**：子图 SSE 事件批量到达（时间线 UX 退化）→ 必须适配 `stream(subgraphs=True)` 重写 `_stream_graph`（去重偏移 / `node` 字段 / 中断提取 / final_answer 全部受影响）；interrupt 冒泡与旧 checkpoint 需 spike 验证。
- **收益**：物理级多图隔离，每 agent 独立演化；面试叙事完整（子图 + 命名空间）。

### 形式二 A′ 平铺图（评审 v2 新增，低风险替代）：一份节点 + `current_agent` 策略字段

顶层图保持现有节点结构（agent_step / execute_tool / 三查 / rewrite 各一份），新增 `current_agent` 状态字段：

1. `agent_step` 按 `current_agent` 查表动态绑定工具子集 + 专属 system prompt（现有 `bind_tools(ALL_TOOLS)` 本就是每次调用时绑定，改查表即可）。
2. `route_grade_documents` 按 `current_agent` 跳过文档评级 → 实现 web_research 的「仅幻觉查」。
3. `should_continue` 按 `current_agent` 查表读取差异化迭代上限。

- **代价**：不是物理隔离的多图，隔离靠工具策略 + prompt；面试叙事稍弱（但对外行为与「编排器 + 专业 agent」叙事完全一致）。
- **收益（关键）**：SSE 事件 schema **零改动**（前端零改动）；interrupt 留在平铺图（**零验证**）；checkpoint 兼容风险≈0；§五风险 #1/#2/#3 整体降级为「不适用」。

### 定稿规则

M7.0 spike 两个骨架各搭一遍（各约半天），按实测数据定稿：

- A′ 全部验收过 → **用 A′ 落地 M7.1-M7.3**，子图形式记为可选后续重构；
- A′ 有硬伤（如动态工具绑定影响 ReAct 质量）→ 回退 A-子图，按 §五对策执行。

外部行为（编排器 + 4 专业 agent、§3.1 工具分配、§3.3 预算分层）在两种形式下**完全一致**，§八拍板结论不受影响。

> **✅ 已定稿（2026-08-30 M7.0 spike）**：A′ 平铺图全部验收通过（冒烟 10/10 + eval 两轮过门槛，run2 recall 0.983 与 M6 持平），**用 A′ 落地 M7.1-M7.3**，A-子图免建（本节保留作为架构叙事与后续可选重构参考）。详见 `升级笔记.md` 进展日志。

---

## 五、P0 风险清单（动手前必须验证）

> 适用性：**A′ 平铺图形式下 #1/#2/#3 不适用**（SSE / interrupt / checkpoint 全部零改动）；A-子图形式下全部适用。

| # | 风险 | 现状证据 | 验证方法 | 对策（若失败） |
|---|---|---|---|---|
| 1 | **子图 SSE 流式降级（A-子图形式下为必然，非可能）**：`.stream()` 默认模式下一个 super-step 只吐一次合并更新——knowledge 子图跑完 8 轮 ReAct，前端时间线才一次性收到全部 thoughts | `_stream_graph` 只解析扁平 `step.items()`（`agent.py:186-207`） | M7.0 spike：A-子图骨架跑真实 SSE 看事件序列 | ① state 同 key 合并只解决数据、**不解决事件到达粒度**，不能当对策；② `stream(subgraphs=True)`：事件变 `(namespace, mode, data)` 元组，`_stream_graph` 的去重偏移、`node` 字段（前端图标映射）、`_extract_interrupts`、final_answer 提取全需重写；③ **首选：改用 A′ 平铺图，风险整体消失** |
| 2 | **HITL interrupt 从子图冒泡（仅 A-子图）**：`_extract_interrupts` + `get_state().tasks` 能否捕获嵌套子图内的 `interrupt()`；`Command(resume=...)` 经父图传播 | interrupt 目前在顶层图节点内（`nodes.py:183`） | M7.0 spike：A-子图骨架内加最小 interrupt 路径（dummy 审批节点即可，不必等 note_write_agent）→ 触发 → 刷新恢复审批卡 → POST resume | 冒泡解析失败则 `_extract_interrupts` 增加嵌套遍历（中断对象结构不变）；A′ 形式下不适用 |
| 3 | **旧 checkpoint 不兼容**：A′ 形式仅增 `total=False` 可选字段，风险≈0；A-子图形式子图 state 通道结构变化，旧 thread 恢复需验证 | `AgentState` 用 `total=False` TypedDict（`state.py`） | M7.0 spike：用升级前创建的会话继续提问 | 拍板已定：清空 `data/langgraph_checkpoints.db`——**SqliteSaver 持有打开连接，必须停服 → 清库 → 起服**，运行中删除无效；兜底：新字段全部带默认值 |
| 4 | **编排错误影响面变大**：web_search/note_write 从 knowledge_agent 移出后，分类错 → 用户要联网却进了 knowledge_agent | 现有四分类 fail-safe 只兜「失败」，不兜「分错」 | eval 集补意图边界用例（明确要求联网的 phrasing） | knowledge_agent 保留 web_search 作回退（见 §3.1）；INTENT_HINTS 回退语义保留 |
| 5 | **token 成本上升**：子 Agent system prompt 各自重复注入偏好上下文 | 偏好注入每次 LLM 调用都拼进 system prompt（`nodes.py:134-140`） | M7.4 eval 报告对比 token_used | 预算分层（§3.3）；目标增幅 ≤15%。「编排层一次注入」现状下**不可行**（偏好是逐调用拼 prompt，非图状态），除非改为向 messages 注入 SystemMessage 并处理裁剪交互——本期不做，仅靠预算分层兜底 |
| 6 | **`_best_answer` 跨轮污染（现存隐患，M7 放大）**：`generate`/`output` 在整个 messages 通道取最长 AIMessage（`nodes.py:344-357`），checkpoint 保留近 24 条历史——之前任何一轮的长答案都可能被选为本轮答案；M7 后 chat 直答（冗长）与知识答案（精炼）同池，误选概率大增 | 两形式通用，必修 | 单测：多轮对话构造「上一轮长答案 + 本轮短答案」，断言 output 取本轮 | `build_input` 记 `turn_start_index`（当前 messages 长度），`_best_answer` 只在 `messages[turn_start_index:]` 内选——纳入 M7.0 |
| 7 | **task_brief 反噬**：一次性分类调用产出的 brief 质量不可控，错误简报注入 system prompt 会主动误导子 Agent（比没有更糟）；structured output 字段变多可能拉低分类质量（P13 function_calling 路径） | M7.1 引入 | 意图边界 eval 用例回归分类准确率 | brief 允许为空，**为空不注入**；仅分类器给出实质描述时注入 |

---

## 六、分阶段实施计划（M7.0-M7.5）

> 每阶段独立可验收、可回滚（git tag + `AGENT_MULTI_AGENT` 旗标双图共存）；50 条 eval 集（`run_eval.py` 新旧对比）是贯穿的硬门槛，**验收一律用「连续 2-3 次均值 ± 噪声带」而非单次跑分**（LLM 固有波动，faithfulness 跨 run 0.87-0.93）。

### M7.0 技术验证 spike（先干这个，结论决定后面走不走）

- [ ] **双骨架对比**：A′ 平铺图与 A-子图各搭最小骨架（编排器 + chat_agent + knowledge 主体），A′ 先验
- [ ] A′ 验证：`current_agent` 查表动态绑定工具 / 差异化 prompt 下行为正常；真实 SSE 确认事件 schema **逐字段不变**（前端零改动硬约束）
- [ ] A-子图验证：真实 SSE 粒度实测（预期批量到达）；最小 interrupt 路径（dummy 审批节点）验证触发 → 刷新恢复 → POST resume；升级前旧会话继续提问
- [ ] **修复 `_best_answer` 跨轮污染**（两形式通用）：`turn_start_index` + 本轮范围选取 + 单测
- [ ] **回退开关**：config 加 `AGENT_MULTI_AGENT`（默认 false），`get_graph()` 按旗标返回新/旧图——回滚不依赖重新部署，eval 新旧对比同进程可跑
- [ ] checkpoint 处理（拍板：清空）：**停服 → 删 `data/langgraph_checkpoints.db` → 起服**
- [ ] 全量 pytest 回归（47 passed 基线）
- [ ] 产出：双骨架实测数据 + 定稿结论（A′ 或 A-子图）追加到 `升级笔记.md`；**两项骨架都不达标则本计划终止，零沉没成本**（骨架代码不合并）

### M7.1 编排器升级

- [ ] **前置：50 条 eval 标注预期意图字段**（Ground Truth，否则「路由准确率」无依据）+ 补意图边界用例（明确要求联网的 phrasing、混合意图 phrasing）
- [ ] `QueryIntent` schema 扩展：intent 保持四分类，新增可选 `task_brief` 字段（编排器给子 Agent 的一句话任务描述；**为空不注入**，防错误简报误导子 Agent）
- [ ] `route_intent` 从两分支扩为四分支（chat / knowledge / web_research / note_write）
- [ ] 更新受影响的 M6 路由/分类测试
- **验收**：意图边界用例路由准确率达标 + fail-safe 用例（分类异常默认 knowledge）通过；全量 pytest 回归

### M7.2 knowledge_agent 专业化（按 M7.0 定稿形式实施）

- [ ] `create_note` 从其工具集移除；web_search 保留作回退（拍板：保留）
- [ ] 子 Agent 专属 system prompt：去掉 note_write 相关规则，工具说明瘦身；加「保存类请求告知用户单独发起」
- [ ] `run_eval.py` 补按 run 的延迟统计口径（否则「P95 劣化 ≤10%」无数据来源）
- **验收**：eval 连续 2-3 次均值不低于 M6 基线噪声带；P95 延迟劣化 ≤10%；全量 pytest 回归

### M7.3 web_research / note_write 子 Agent

- [ ] web_research_agent：web_search 专职 + 仅幻觉查 + 信源引用格式（无 answer_quality，明示取舍见 §七）
- [ ] note_write_agent：查重 → create_note（HITL）；`_pending_approval_payload` 恢复逻辑验证（A′ 零改动 / A-子图适配子图快照）
- [ ] 冒烟必须**经编排器路由**命中专职 agent（`verify_web_search.py` 是工具直调，不算路由覆盖）
- **验收**：`verify_web_search.py` 5/5 回归 + 经路由的真实 SSE 冒烟；审批 → 批准/拒绝 → 继续对话全流程手工回归；token 增幅 ≤15%；全量 pytest 回归

### M7.4 可观测与收尾

- [ ] Langfuse trace 按 agent 打标（A′ 按节点内 `current_agent`；A-子图按子图节点名）；本地审计降级路径同步
- [ ] `agent_sessions` 记录命中的 agent 路由（方便后续分析路由准确率）
- [ ] eval 新旧对比报告（`eval/reports/`，利用 `AGENT_MULTI_AGENT` 同进程跑双图）；D13 落地回顾；`待做清单.md` 盘点
- **验收**：eval 报告出结论，文档闭环

### M7.5（可选，不纳入本期）Supervisor 循环编排

- [ ] 仅当 M7.0-M7.4 验收全过且确有混合意图需求时启动：手写 supervisor 节点（不引库），支持 web_research → note_write 顺序派单
- [ ] 机制前置：`iteration` 共享字段必须派单级重置 + 新增派单计数器（上限 ≤3），否则子 Agent 迭代上限失效
- [ ] 验收：混合意图用例（"搜一下 X 并保存成笔记"）端到端通过；编排轮次 ≤3 熔断生效

---

## 七、明确不做（YAGNI 边界）

- 不引 `langgraph-supervisor` / CrewAI / AutoGen 等第二框架（守 D1）
- 不做 Swarm / 自由 handoff
- 不做多模型多 Agent（DeepSeek 单 provider 跑全部角色；qwen 只做裁判与 embedding，既有分工不变）
- 不拆 graph_analysis_agent（图谱工具仅 1 个，不够格）
- 不给 MCP Server 做多 Agent（MCP 与 agent 共享工具层的既有设计不变）
- 不做「编排层一次偏好注入」（现状逐调用拼 prompt，改造收益低风险高，本期靠预算分层兜底）
- web_research_agent 不做 answer_quality（跑题风险由 prompt 约束，明示取舍）
- 若 A′ 验证通过，不做物理级多图隔离（隔离靠工具策略 + prompt，子图形式记为可选后续重构）

---

## 八、决策拍板（2026-08-30，按推荐执行）

1. **方案 A 起步 ✅；M7.5（Supervisor 循环编排）不纳入本期**，待 M7.0-M7.4 验收后按需启动。
2. **web_search 保留在 knowledge_agent 作回退 ✅**（意图误判时 agent 仍有出路）。
3. **旧 checkpoint 直接清空 ✅**：`data/langgraph_checkpoints.db`，最简方案。
4. **新增 `task_brief` 字段 ✅**：编排器给子 Agent 传任务简报，M7.5 复用价值高；**为空不注入**（评审 v2 补充）。
5. **实现形式 ✅（评审 v2 新增；M7.0 已定稿 A′）**：M7.0 双骨架对比，A′ 平铺图优先——验证通过即用 A′ 落地（SSE/HITL/checkpoint 零改动），A-子图为备选；外部行为与拍板结论不受影响。**2026-08-30 spike 验收通过，A′ 定稿。**
6. **回退开关 ✅（评审 v2 新增）**：`AGENT_MULTI_AGENT` 配置旗标双图共存，回滚不依赖重新部署。已实现（默认 false）。
