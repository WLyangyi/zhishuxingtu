# -*- coding: utf-8 -*-
"""faiss 路径兼容性:faiss 的 C++ IO 用窄字符 fopen,Windows 下非 ASCII 绝对路径会写盘失败。

背景:仓库目录「知枢星图」含中文,按绝对路径重建消融索引时 `faiss.write_index` 报
`could not open ... No such file or directory`。`_faiss_safe_path` 在目标位于 cwd 下时
改传 ASCII 相对路径,规避该问题。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.vector_store import _faiss_safe_path


def test_ascii_relative_path_passthrough():
    assert _faiss_safe_path(os.path.join("data", "faiss_index")) == os.path.join(
        "data", "faiss_index"
    )


def test_path_outside_cwd_keeps_absolute():
    outside = os.path.abspath(os.path.join(os.getcwd(), os.pardir, "elsewhere-index"))
    assert _faiss_safe_path(outside) == outside


def test_non_ascii_cwd_is_rewritten_to_ascii_relative():
    if all(ord(ch) < 128 for ch in os.getcwd()):
        import pytest

        pytest.skip("当前工作目录全 ASCII,本机无需该兜底")
    target = os.path.join(os.getcwd(), "data", "ablation-overlap0-faiss", "index.faiss")
    safe = _faiss_safe_path(target)
    assert not os.path.isabs(safe)
    assert all(ord(ch) < 128 for ch in safe)
    assert os.path.abspath(safe) == target
