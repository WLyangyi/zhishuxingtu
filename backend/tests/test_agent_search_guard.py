# -*- coding: utf-8 -*-
"""回归用例:重复检索语义判重(病灶B)与迭代耗尽兜底。"""
import json

from app.services.agent.nodes import (
    _duplicate_search_error,
    _fallback_from_documents,
    _is_semantic_duplicate,
    _normalize_query,
)


def test_normalize_query_strips_punct_and_filler():
    assert _normalize_query(" 帮我查一下 吴浩阳 的简历？ ") == "吴浩阳简历"


def test_semantic_duplicate_exact_after_normalization():
    assert _is_semantic_duplicate("吴浩阳 的简历", "吴浩阳简历")


def test_semantic_duplicate_superset_of_successful_query():
    # b010 回归:第一次检索"吴浩阳"已返回结果,后续"吴浩阳 简历 项目经历"属同意图扩展
    assert _is_semantic_duplicate("吴浩阳 简历 项目经历", "吴浩阳")


def test_semantic_duplicate_keeps_different_entities():
    assert not _is_semantic_duplicate("吴浩阳", "Cloud Code 技巧")
    # 对比型问题需要分别检索两篇不同笔记,不应被判重
    assert not _is_semantic_duplicate("Cloud Code 六技巧", "Cloud Code 六个小技巧")


def test_duplicate_search_error_allows_retry_after_empty_result():
    log = [{"tool": "search_notes", "status": "success", "args": {"query": "量子引力"}, "result": "[]"}]
    assert _duplicate_search_error("量子引力统一理论", log) == ""


def test_duplicate_search_error_blocks_rephrase_when_prior_had_results():
    log = [
        {
            "tool": "search_notes",
            "status": "success",
            "args": {"query": "吴浩阳"},
            "result": json.dumps([{"id": "n1", "title": "吴浩阳简历", "snippet": "..."}], ensure_ascii=False),
        }
    ]
    assert "重复" in _duplicate_search_error("吴浩阳 简历 项目经历", log)


def test_fallback_from_documents_lists_titles():
    docs = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}, {"id": "3", "title": "A"}]
    out = _fallback_from_documents(docs)
    assert "A" in out and "B" in out
    assert out.count("- A") == 1
    assert _fallback_from_documents([]) == ""
