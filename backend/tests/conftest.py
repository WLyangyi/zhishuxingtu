# -*- coding: utf-8 -*-
"""测试环境兜底:本机 WMI 查询卡死、transformers→torch 连带阻塞会拖住 import 阶段,
与 eval/run_eval.py 顶部保持同一套 workaround,避免 pytest 收集用例时卡住。"""
import platform
import sys

sys.modules.setdefault("transformers", None)
platform.win32_ver = lambda *a, **k: ("", "", "", "")
platform.machine = lambda: "AMD64"
