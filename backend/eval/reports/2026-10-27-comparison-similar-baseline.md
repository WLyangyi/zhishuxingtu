# Agentic RAG 对比报告(agent-v1)

生成时间:2026-10-27 04:54  评测条数:4
裁判口径:skip-judge

## 总体指标

| 指标 | 旧基线 baseline | 新 agent |
|---|---|---|
| recall@k | 0.000 | 1.000 |
| faithfulness | — | — |
| answer_relevancy | — | — |
| context_recall | — | — |
| answer_coverage | — | — |
| pass 率 | — | 4/4 = 100.0% |

> context_recall / answer_coverage 为 Phase 3 新增指标,仅对 agent 侧计算(基线侧不参与消融对比,故留空)。

## 按分类分桶

| 分类 | 条数 | recall(b/a) | faithful(b/a) | relevancy(b/a) | ctx_recall(a) | coverage(a) |
|---|---|---|---|---|---|---|
| similar_docs | 4 | 0.000/1.000 | —/— | —/— | — | — |

## Agent 意图分布与成本

- 意图分布: {'knowledge': 4}
- agent 平均工具调用次数: 3.50
- agent 平均 token 消耗: 9994
- agent 平均成本(估算): ¥0.0200/条

## 失败归因分布

| 归因 | 条数 |
|---|---|
| pass | 4 |

## 延迟(M7.2 口径,graph.stream 端到端)

| 链路 | 均值 ms | P95 ms |
|---|---|---|
| baseline | — | — |
| agent | 10013 | 10475 |

- 路由准确率(vs expected_intent): 4/4 = 100.0%


## 逐条明细

| id | 分类 | recall(b/a) | faithful(b/a) | relevancy(b/a) | ctx_recall(a) | coverage(a) | 判定 | 失败归因 | 问题 |
|---|---|---|---|---|---|---|---|---|---|
| s01 | similar_docs | 0.000/1.000 | —/— | —/— | — | — | 通过 | — | 知识库里两篇标题都叫《Test PDF》的笔记内容完全相同吗？各自来源是什么？ |
| s02 | similar_docs | 0.000/1.000 | —/— | —/— | — | — | 通过 | — | 《Cloud Code六个小技巧》和《Cloud Code六技巧》是同一篇笔记的 |
| s03 | similar_docs | 0.000/1.000 | —/— | —/— | — | — | 通过 | — | 两篇标题同为《5月10日科技行业动态与产品发布》的笔记内容一致吗？各自包含哪些动 |
| s04 | similar_docs | 0.000/1.000 | —/— | —/— | — | — | 通过 | — | 《克劳德code安装与配置指南》和《15个Cloud Code实用技巧与优化方法 |
