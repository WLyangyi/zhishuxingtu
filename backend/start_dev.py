# -*- coding: utf-8 -*-
"""本地开发后端启动脚本（含本机环境 workaround）。

用法：
    cd backend
    .venv\\Scripts\\python.exe -u start_dev.py

为什么需要这个垫片（而不是直接 uvicorn app.main:app）：
1. 本机 openai SDK 构造请求头时会调用 platform.platform()/platform.uname()，
   内部触发 Windows WMI 查询会卡死。测试 conftest.py 只 mock 了
   system/win32_ver/machine，裸起 uvicorn 仍会挂死，这里补齐 platform/uname mock。
2. transformers→torch 原生 DLL 加载在 import 阶段会长时间卡死，本项目 embedding
   走 DashScope 远程 API，不需要 transformers，标记为不可用让其走 except 分支。
3. 本机 openai SDK(httpx 0.28) 走 HTTP_PROXY 会卡死，curl 直连 api.deepseek.com
   正常，故清除代理变量让 SDK 直连。
4. 默认开启 A′ 多 Agent 图（AGENT_MULTI_AGENT=true），与"保存为笔记"问题复现场景一致。

以上均为本机环境适配，不修改任何业务代码。生产/其他环境直接用标准 uvicorn 启动即可。
"""
import os
import platform
import sys

sys.modules.setdefault("transformers", None)
platform.system = lambda: "Windows"
platform.win32_ver = lambda *a, **k: ("", "", "", "")
platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"
platform.platform = lambda *a, **k: "Windows-AMD64"
platform.uname = lambda: ("Windows", "", "", "", "AMD64", "")
platform.python_version = lambda: "3.11.0"

for _k in (
    "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
    "ALL_PROXY", "all_proxy",
):
    os.environ.pop(_k, None)

import uvicorn

if __name__ == "__main__":
    os.environ.setdefault("AGENT_MULTI_AGENT", "true")
    print("[start_dev] AGENT_MULTI_AGENT=", os.environ.get("AGENT_MULTI_AGENT"), flush=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
