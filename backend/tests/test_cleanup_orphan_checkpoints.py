# -*- coding: utf-8 -*-
"""二期 2.7 orphan checkpoint 清理脚本测试（TDD）。

模拟断流重放产生的 checkpoint 分叉树，验证：
- 活跃路径判定（rowid 最大为最新 + parent_checkpoint_id 回溯）
- orphan 分支识别（子树收集，分支根 = parent 在活跃路径）
- plan_cleanup dry-run 计划（不删）
- execute_cleanup 删除 orphan、保留活跃、连带 writes
- thread_id 过滤、checkpoint_id 精确指定、backup
"""
import os
import sys
import sqlite3
import shutil

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _SCRIPTS)
import cleanup_orphan_checkpoints as oc  # noqa: E402


SCHEMA = """
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,
    metadata BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
"""


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    return conn


def _add_cp(conn, thread_id, checkpoint_id, parent, payload=b"x" * 100):
    conn.execute(
        "INSERT INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata) "
        "VALUES (?, '', ?, ?, 'json', ?, ?)",
        (thread_id, checkpoint_id, parent, payload, b"{}"),
    )


def _add_write(conn, thread_id, checkpoint_id, task_id="t1", idx=0, payload=b"w" * 10):
    conn.execute(
        "INSERT INTO writes (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value) "
        "VALUES (?, '', ?, ?, ?, 'msgs', 'json', ?)",
        (thread_id, checkpoint_id, task_id, idx, payload),
    )


def _branch_tree(conn):
    """构造 abort+重放分叉树：
    CP1(root) -> CP2 -> CP3 （aborted 分支）
    CP1        -> CP4 -> CP5 （重放新分支，最新，rowid 最大）
    """
    _add_cp(conn, "T", "CP1", None)
    _add_cp(conn, "T", "CP2", "CP1")
    _add_cp(conn, "T", "CP3", "CP2")
    _add_cp(conn, "T", "CP4", "CP1")
    _add_cp(conn, "T", "CP5", "CP4")
    for cid in ("CP1", "CP2", "CP3", "CP4", "CP5"):
        _add_write(conn, "T", cid)
    conn.commit()


def _cp_list():
    return [
        {"rowid": 1, "thread_id": "T", "checkpoint_ns": "", "checkpoint_id": "CP1", "parent_checkpoint_id": None, "size": 100},
        {"rowid": 2, "thread_id": "T", "checkpoint_ns": "", "checkpoint_id": "CP2", "parent_checkpoint_id": "CP1", "size": 100},
        {"rowid": 3, "thread_id": "T", "checkpoint_ns": "", "checkpoint_id": "CP3", "parent_checkpoint_id": "CP2", "size": 100},
        {"rowid": 4, "thread_id": "T", "checkpoint_ns": "", "checkpoint_id": "CP4", "parent_checkpoint_id": "CP1", "size": 100},
        {"rowid": 5, "thread_id": "T", "checkpoint_ns": "", "checkpoint_id": "CP5", "parent_checkpoint_id": "CP4", "size": 100},
    ]


# ---------- 活跃路径判定 ----------

def test_compute_active_path_single_chain_all_active():
    chain = [
        {"rowid": 1, "checkpoint_id": "A", "parent_checkpoint_id": None},
        {"rowid": 2, "checkpoint_id": "B", "parent_checkpoint_id": "A"},
        {"rowid": 3, "checkpoint_id": "C", "parent_checkpoint_id": "B"},
    ]
    assert oc.compute_active_checkpoint_ids(chain) == {"A", "B", "C"}


def test_compute_active_path_with_branch():
    assert oc.compute_active_checkpoint_ids(_cp_list()) == {"CP1", "CP4", "CP5"}


def test_compute_active_path_empty():
    assert oc.compute_active_checkpoint_ids([]) == set()


# ---------- orphan 分支识别 ----------

def test_find_orphan_branches_identifies_aborted_branch():
    branches = oc.find_orphan_branches(_cp_list())
    assert len(branches) == 1
    b = branches[0]
    assert b["checkpoint_id"] == "CP2"
    assert b["parent_checkpoint_id"] == "CP1"
    assert set(b["subtree_ids"]) == {"CP2", "CP3"}
    assert b["subtree_size"] == 2


def test_find_orphan_branches_clean_chain_no_orphan():
    chain = [
        {"rowid": 1, "checkpoint_id": "A", "parent_checkpoint_id": None},
        {"rowid": 2, "checkpoint_id": "B", "parent_checkpoint_id": "A"},
    ]
    assert oc.find_orphan_branches(chain) == []


# ---------- plan / execute ----------

def test_plan_cleanup_dry_run_reports_orphan():
    conn = _make_db()
    _branch_tree(conn)
    plan = oc.plan_cleanup(conn)
    assert plan["total_checkpoints"] == 2  # CP2 + CP3
    assert plan["total_writes"] == 2
    assert plan["branches"][0]["checkpoint_id"] == "CP2"
    # dry-run：数据仍在
    n = conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
    assert n == 5


def test_execute_cleanup_removes_orphan_keeps_active():
    conn = _make_db()
    _branch_tree(conn)
    plan = oc.plan_cleanup(conn)
    result = oc.execute_cleanup(conn, plan)
    assert result["deleted_checkpoints"] == 2
    assert result["deleted_writes"] == 2
    remaining_cp = {r[0] for r in conn.execute("SELECT checkpoint_id FROM checkpoints")}
    assert remaining_cp == {"CP1", "CP4", "CP5"}
    remaining_w = {r[0] for r in conn.execute("SELECT checkpoint_id FROM writes")}
    assert remaining_w == {"CP1", "CP4", "CP5"}


def test_plan_thread_filter_only_target_thread():
    conn = _make_db()
    _branch_tree(conn)
    _add_cp(conn, "T2", "X1", None)
    _add_cp(conn, "T2", "X2", "X1")
    conn.commit()
    plan_t2 = oc.plan_cleanup(conn, thread_id="T2")
    assert plan_t2["total_checkpoints"] == 0  # T2 单链无 orphan
    plan_all = oc.plan_cleanup(conn)
    assert plan_all["total_checkpoints"] == 2  # 仅 T 的 orphan


def test_checkpoint_id_specify_cleans_subtree():
    conn = _make_db()
    _branch_tree(conn)
    plan = oc.plan_cleanup(conn, checkpoint_id="CP2")
    assert plan["total_checkpoints"] == 2  # CP2 子树 = CP2 + CP3
    oc.execute_cleanup(conn, plan)
    remaining = {r[0] for r in conn.execute("SELECT checkpoint_id FROM checkpoints")}
    assert remaining == {"CP1", "CP4", "CP5"}


def test_checkpoint_id_specify_non_orphan_noop():
    conn = _make_db()
    _branch_tree(conn)
    plan = oc.plan_cleanup(conn, checkpoint_id="CP4")  # CP4 在活跃路径，非 orphan
    assert plan["total_checkpoints"] == 0
    n = conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
    assert n == 5


# ---------- backup ----------

def test_backup_db_creates_file(tmp_path):
    db = tmp_path / "test.db"
    c = sqlite3.connect(str(db))
    c.execute("CREATE TABLE t (x)")
    c.commit()
    c.close()
    backup = oc.backup_db(str(db))
    assert os.path.exists(backup)
    assert backup != str(db)
    assert os.path.getsize(backup) == os.path.getsize(str(db))
