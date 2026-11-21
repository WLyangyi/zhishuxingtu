# -*- coding: utf-8 -*-
"""二期 2.7 orphan checkpoint 清理脚本。

背景：阶段 0 断流重放（任务 0.2）会让 aborted 分支的 checkpoint 留在 SqliteSaver 的 db 里，
SqliteSaver 无按分支删除 API，DB 随重放持续涨。本脚本按 thread_id + checkpoint_id 安全清理
orphan 分支：一个 checkpoint 不在该 thread「从最新 checkpoint（rowid 最大）沿
parent_checkpoint_id 回溯到根」的活跃路径上，即为 orphan。

安全设计：
- 默认 dry-run，只列将删除的，不真删；--apply 才删
- dry-run 用只读连接打开，避免误写
- 删除在事务内，先删 writes 再删 checkpoints
- 活跃路径上的 checkpoint 永不删除（重放分叉后活跃分支不受影响）
- 可选 --backup 清理前复制 db 文件

运行（backend 目录下）：
  python scripts\\cleanup_orphan_checkpoints.py                       # dry-run
  python scripts\\cleanup_orphan_checkpoints.py --apply               # 真删
  python scripts\\cleanup_orphan_checkpoints.py --thread-id <id> --apply
  python scripts\\cleanup_orphan_checkpoints.py --checkpoint-id <id> --apply
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time
from collections import defaultdict

DEFAULT_DB = os.path.join("data", "langgraph_checkpoints.db")

_CHECKPOINT_COLS = (
    "rowid, thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, length(checkpoint)"
)


def compute_active_checkpoint_ids(checkpoints):
    """从最新 checkpoint（rowid 最大）沿 parent_checkpoint_id 回溯，返回活跃路径 checkpoint_id 集合。"""
    if not checkpoints:
        return set()
    latest = max(checkpoints, key=lambda c: c["rowid"])
    by_id = {c["checkpoint_id"]: c for c in checkpoints}
    active = set()
    seen = set()
    node = latest
    while node is not None:
        cid = node["checkpoint_id"]
        if cid in seen:
            break
        seen.add(cid)
        active.add(cid)
        par = node.get("parent_checkpoint_id")
        if par is None or par not in by_id:
            break
        node = by_id[par]
    return active


def _collect_subtree(root_id, by_id):
    """收集 root_id 及其所有后代 checkpoint_id，按 rowid 升序返回。"""
    children = defaultdict(list)
    for c in by_id.values():
        p = c.get("parent_checkpoint_id")
        if p:
            children[p].append(c["checkpoint_id"])
    subtree = []
    seen = set()
    stack = [root_id]
    while stack:
        cid = stack.pop()
        if cid in seen:
            continue
        seen.add(cid)
        subtree.append(cid)
        stack.extend(children.get(cid, []))
    subtree.sort(key=lambda cid: by_id[cid]["rowid"])
    return subtree


def find_orphan_branches(checkpoints):
    """返回 orphan 分支列表。

    orphan = 不在活跃路径上的 checkpoint。分支根 = orphan 中 parent 在活跃路径（或 None）
    的节点，带其完整子树。这样清理一个分支根即清掉整条 aborted 分支。
    """
    active = compute_active_checkpoint_ids(checkpoints)
    by_id = {c["checkpoint_id"]: c for c in checkpoints}
    orphan_ids = {c["checkpoint_id"] for c in checkpoints if c["checkpoint_id"] not in active}
    branches = []
    for c in checkpoints:
        cid = c["checkpoint_id"]
        if cid not in orphan_ids:
            continue
        parent = c.get("parent_checkpoint_id")
        # 分支根：parent 不在 orphan_ids（即 parent 在活跃路径或为 None）
        if parent is not None and parent in orphan_ids:
            continue
        subtree = _collect_subtree(cid, by_id)
        branches.append({
            "checkpoint_id": cid,
            "parent_checkpoint_id": parent,
            "subtree_ids": subtree,
            "subtree_size": len(subtree),
        })
    return branches


def _load_checkpoints(conn, thread_id=None):
    sql = f"SELECT {_CHECKPOINT_COLS} FROM checkpoints"
    params = ()
    if thread_id:
        sql += " WHERE thread_id = ?"
        params = (thread_id,)
    rows = conn.execute(sql, params).fetchall()
    return [
        {"rowid": r[0], "thread_id": r[1], "checkpoint_ns": r[2],
         "checkpoint_id": r[3], "parent_checkpoint_id": r[4], "size": r[5]}
        for r in rows
    ]


def plan_cleanup(conn, thread_id=None, checkpoint_id=None):
    """查询并返回清理计划（dry-run，不删）。"""
    cps = _load_checkpoints(conn, thread_id=thread_id)
    groups = defaultdict(list)
    for c in cps:
        groups[(c["thread_id"], c["checkpoint_ns"])].append(c)

    branches = []
    for (tid, ns), group_cps in groups.items():
        for b in find_orphan_branches(group_cps):
            if checkpoint_id is not None and b["checkpoint_id"] != checkpoint_id:
                continue
            branches.append({
                "thread_id": tid,
                "checkpoint_ns": ns,
                "checkpoint_id": b["checkpoint_id"],
                "parent_checkpoint_id": b["parent_checkpoint_id"],
                "subtree_ids": b["subtree_ids"],
                "subtree_size": b["subtree_size"],
            })

    total_writes = 0
    total_bytes = 0
    for b in branches:
        placeholders = ",".join("?" for _ in b["subtree_ids"])
        params = [b["thread_id"], b["checkpoint_ns"], *b["subtree_ids"]]
        w = conn.execute(
            f"SELECT COUNT(*) FROM writes WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id IN ({placeholders})",
            params,
        ).fetchone()[0]
        total_writes += w
        row = conn.execute(
            f"SELECT COALESCE(SUM(length(checkpoint)),0) FROM checkpoints "
            f"WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id IN ({placeholders})",
            params,
        ).fetchone()
        total_bytes += row[0] or 0

    return {
        "branches": branches,
        "total_checkpoints": sum(b["subtree_size"] for b in branches),
        "total_writes": total_writes,
        "total_bytes": total_bytes,
        "threads": {b["thread_id"] for b in branches},
    }


def execute_cleanup(conn, plan):
    """执行删除：事务内先删 writes 再删 checkpoints。返回删除统计。"""
    deleted_cp = 0
    deleted_w = 0
    conn.execute("BEGIN")
    try:
        for b in plan["branches"]:
            tid, ns = b["thread_id"], b["checkpoint_ns"]
            for cid in b["subtree_ids"]:
                cur = conn.execute(
                    "DELETE FROM writes WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                    (tid, ns, cid),
                )
                deleted_w += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
                conn.execute(
                    "DELETE FROM checkpoints WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                    (tid, ns, cid),
                )
                deleted_cp += 1
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {
        "deleted_checkpoints": deleted_cp,
        "deleted_writes": deleted_w,
        "freed_bytes": plan.get("total_bytes", 0),
    }


def backup_db(db_path):
    """复制 db 文件到带时间戳的备份。返回备份路径。"""
    backup_path = f"{db_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _print_plan(plan, db_path):
    print(f"DB: {db_path}")
    print(f"orphan 分支数: {len(plan['branches'])}")
    print(f"将删除 checkpoint 行: {plan['total_checkpoints']}")
    print(f"将删除 writes 行: {plan['total_writes']}")
    print(f"预计释放: {plan['total_bytes'] / 1024 / 1024:.2f} MB")
    for b in plan["branches"][:20]:
        print(f"  thread={b['thread_id'][:40]}  branch_root={b['checkpoint_id']}  subtree={b['subtree_size']}")
    if len(plan["branches"]) > 20:
        print(f"  ... 共 {len(plan['branches'])} 个分支（仅列前 20）")


def main(argv=None):
    parser = argparse.ArgumentParser(description="清理 SqliteSaver orphan checkpoint 分支")
    parser.add_argument("--db", default=DEFAULT_DB, help="checkpoint db 路径")
    parser.add_argument("--thread-id", default=None, help="只处理指定 thread")
    parser.add_argument("--checkpoint-id", default=None, help="只清理该 checkpoint 为根的 orphan 子树")
    parser.add_argument("--apply", action="store_true", help="真正删除（默认 dry-run）")
    parser.add_argument("--backup", action="store_true", help="清理前备份 db 文件")
    args = parser.parse_args(argv)

    if not os.path.exists(args.db):
        print(f"db 不存在: {args.db}")
        return 2

    if args.backup:
        backup = backup_db(args.db)
        print(f"已备份 db → {backup}")

    # dry-run 用只读连接，apply 才用可写连接
    if args.apply:
        conn = sqlite3.connect(args.db)
    else:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        plan = plan_cleanup(conn, thread_id=args.thread_id, checkpoint_id=args.checkpoint_id)
        _print_plan(plan, args.db)
        if not args.apply:
            print("\n（dry-run 模式，加 --apply 才真正删除）")
            return 0
        result = execute_cleanup(conn, plan)
        print(
            f"\n已删除：checkpoint {result['deleted_checkpoints']} 行，"
            f"writes {result['deleted_writes']} 行，"
            f"释放约 {result['freed_bytes'] / 1024 / 1024:.2f} MB"
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
