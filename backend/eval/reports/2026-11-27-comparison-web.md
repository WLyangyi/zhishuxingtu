# Agentic RAG 对比报告(agent-v1)

生成时间:2026-11-27 01:50  评测条数:5
裁判口径:glm / glm-5.3-flash

## 总体指标

| 指标 | 旧基线 baseline | 新 agent |
|---|---|---|
| recall@k | — | — |
| faithfulness | — | 0.800 |
| answer_relevancy | — | 0.780 |
| context_recall | — | 0.894 |
| answer_coverage | — | 0.666 |
| pass 率 | — | 1/5 = 20.0% |

> context_recall / answer_coverage 为 Phase 3 新增指标,仅对 agent 侧计算(基线侧不参与消融对比,故留空)。

## 按分类分桶

| 分类 | 条数 | recall(b/a) | faithful(b/a) | relevancy(b/a) | ctx_recall(a) | coverage(a) |
|---|---|---|---|---|---|---|
| web_search | 5 | —/— | —/0.800 | —/0.780 | 0.894 | 0.666 |

## Agent 意图分布与成本

- 意图分布: {'web_search': 5}
- agent 平均工具调用次数: 6.00
- agent 平均 token 消耗: 36917
- agent 平均成本(估算): ¥0.0738/条

## 失败归因分布

| 归因 | 条数 |
|---|---|
| pass | 1 |
| judge_error | 1 |
| generation_hallucination | 1 |
| answer_incomplete | 1 |
| answer_coverage | 1 |

## 延迟(M7.2 口径,graph.stream 端到端)

| 链路 | 均值 ms | P95 ms |
|---|---|---|
| baseline | — | — |
| agent | 12888 | 19314 |

- 路由准确率(vs expected_intent): 5/5 = 100.0%


## 逐条明细

| id | 分类 | recall(b/a) | faithful(b/a) | relevancy(b/a) | ctx_recall(a) | coverage(a) | 判定 | 失败归因 | 问题 |
|---|---|---|---|---|---|---|---|---|---|
| w01 | web_search | —/— | —/0.530 | —/0.950 | 0.800 | 1.000 | 未通过 | generation_hallucination | 帮我上网查一下 Python 3.12 官方版本有哪些主要新特性 |
| w02 | web_search | —/— | —/0.810 | —/0.950 | 0.670 | 0.330 | 未通过 | answer_coverage | 需要联网搜索：FastAPI 官方文档推荐的异步数据库用法是什么 |
| w03 | web_search | —/— | —/— | —/0.950 | 1.000 | 1.000 | 未通过 | judge_error | 帮我上网查一下 HTTP 状态码 429 的官方定义和常见处理建议 |
| w04 | web_search | —/— | —/0.860 | —/0.950 | 1.000 | 1.000 | 通过 | — | 需要联网搜索：PEP 8 对 Python 代码缩进的官方建议是什么 |
| w05 | web_search | —/— | —/1.000 | —/0.100 | 1.000 | 0.000 | 未通过 | answer_incomplete | 帮我上网查一下 SQLite 官方文档中 WAL 模式的作用 |
