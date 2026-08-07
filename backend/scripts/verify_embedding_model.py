# -*- coding: utf-8 -*-
"""
M0-1: 验证 qwen3.7-text-embedding 模型真实可用性。

用法:
    F:\\ANACONDA\\python.exe scripts/verify_embedding_model.py [--model <模型ID>]

默认模型: settings.QWEN_EMBEDDING_MODEL (若配置未加则退回 settings.DASHSCOPE_EMBEDDING_MODEL)

流程:
    1. 不带 dimensions 参数调用 /embeddings,拿模型真实默认维度
    2. 带 dimensions=<该维度> 再调一次,确认模型是否接受该参数

打印模型 ID / 成功与否 / 默认维度 / dimensions 参数支持情况。失败以非零码退出。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402
from app.core.config import settings  # noqa: E402

EMBEDDING_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
TEST_INPUT = "知枢星图个人知识库系统,用于测试向量维度。"


def call_embedding(model: str, api_key: str, payload: dict) -> tuple:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(EMBEDDING_URL, headers=headers, json=payload, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text[:500]}
    return resp.status_code, data


def probe(model: str, api_key: str) -> tuple:
    print("=" * 60)
    print(f"模型 ID: {model}")
    print(f"测试输入: {TEST_INPUT!r}")
    print("=" * 60)

    if not api_key:
        print("[失败] DASHSCOPE_API_KEY 未配置,无法验证。")
        sys.exit(1)

    # Case 1: 不带 dimensions,拿默认维度
    print("\n[Case 1] 不带 dimensions 参数 ...")
    status, data = call_embedding(model, api_key, {
        "model": model,
        "input": TEST_INPUT,
        "encoding_format": "float",
    })

    if status != 200 or not data.get("data"):
        print(f"[失败] HTTP {status}")
        print(f"       响应: {json.dumps(data, ensure_ascii=False)[:500]}")
        return False

    emb = data["data"][0]["embedding"]
    default_dim = len(emb)
    print(f"[通过] HTTP {status}, 默认维度 = {default_dim}")

    # Case 2: 带 dimensions 参数
    print(f"\n[Case 2] 带 dimensions={default_dim} 参数 ...")
    status2, data2 = call_embedding(model, api_key, {
        "model": model,
        "input": TEST_INPUT,
        "dimensions": default_dim,
        "encoding_format": "float",
    })

    if status2 == 200 and data2.get("data"):
        dim2 = len(data2["data"][0]["embedding"])
        print(f"[通过] HTTP {status2}, 返回维度 = {dim2}")
        print(f"[结论] 模型接受 dimensions 参数;实测维度 = {default_dim}")
        return default_dim, True
    else:
        print(f"[失败] HTTP {status2}")
        print(f"       响应: {json.dumps(data2, ensure_ascii=False)[:500]}")
        print(f"[结论] 模型不支持 dimensions 参数(需省略该字段);实测默认维度 = {default_dim}")
        return default_dim, False


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 DashScope embedding 模型")
    parser.add_argument("--model", default=None, help="要验证的模型 ID")
    args = parser.parse_args()

    model = args.model or getattr(settings, "QWEN_EMBEDDING_MODEL", None) \
        or getattr(settings, "DASHSCOPE_EMBEDDING_MODEL", None)
    if not model:
        print("[失败] 未指定模型,且 settings 中读不到 QWEN_EMBEDDING_MODEL / DASHSCOPE_EMBEDDING_MODEL。")
        sys.exit(1)

    result = probe(model, settings.DASHSCOPE_API_KEY)
    if result is False:
        print("\n[M0-1 闸门] 验证失败。按用户决定,不自动换模型,停止并反馈。")
        sys.exit(1)

    dim, accepts_dim = result
    print("\n" + "=" * 60)
    print(f"[M0-1 结果] 模型: {model} | 维度: {dim} | 接受 dimensions 参数: {accepts_dim}")
    print("=" * 60)


if __name__ == "__main__":
    main()
