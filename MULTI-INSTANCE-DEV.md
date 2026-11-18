# 多实例并行开发：启动与避冲突指南

> 读者：在同一项目的另一个分支上工作的 AI / 开发者
> 更新：2026-11-18 · 主工作区 `front1` @ `7aef2b7`
> 目的：让你能独立启动前后端、跑测试、看页面，同时**不影响正在运行的主实例**

---

## 0. 先看清谁在占用

主工作区 `D:\知枢星图`（分支 `front1`）当前有一个活跃实例：

| 服务 | 地址 | 进程 PID（示例） |
|---|---|---|
| 后端 | `http://127.0.0.1:8000` | 14716 |
| 前端 | `http://localhost:5173` | 7100 |

**硬性规则：**

1. 不要 kill 监听 `8000` / `5173` 的进程，也不要 `taskkill /IM python.exe`、`taskkill /IM node.exe` 这类无差别清理。
2. 不要在 `D:\知枢星图` 主工作区里 `git checkout` 别的分支——会直接改掉别人正在编辑的文件。
3. 两个后端**不要指向同一个 SQLite 文件**；两个后端**不要共用同一个 FAISS 索引目录**（后端退出时会写盘）。
4. 不要修改/提交主工作区的 `backend/.env`；`.env` 只存在于本地，永不入库。
5. 只在自己的分支提交；提交前先 `git status` 确认没有混入别人的文件。

---

## 1. 端口分配（固定，别抢）

| 实例 | 后端 | 前端 | 说明 |
|---|---|---|---|
| 主实例（已占用） | `8000` | `5173` | 不要使用 |
| **你的并行实例** | **`8010`** | **`5180`** | 本文后续命令均按这套 |
| 备用 | `8020` | `5190` | 8010/5180 被占时再用 |

> 不要用 8001 / 5174：历史上这两个端口出现过 TIME_WAIT 残留和调试进程，容易误连到旧实例。

---

## 2. 第一步：在自己的 worktree 里工作

不要在主目录切分支。用独立 worktree（项目里已有一个：`.claude/worktrees/main-agent-fix`，分支 `worktree-main-agent-fix`）。

新建一个：

```bat
cd /d D:\知枢星图
git worktree add D:\知枢星图-worktrees\<your-branch> <your-branch>
```

如果分支还不存在：

```bat
git worktree add -b <your-branch> D:\知枢星图-worktrees\<your-branch> origin/main
```

之后所有命令都在 `D:\知枢星图-worktrees\<your-branch>` 下执行。

---

## 3. 选模式：只改前端，还是也改后端

### 模式 A：只改前端（最省事，零数据冲突）

直接复用主实例的后端 `8000`，你只起自己的前端：

```bat
cd /d D:\知枢星图-worktrees\<your-branch>\frontend
npm install
npm run dev -- --port 5180 --strictPort
```

如果你的分支里 `vite.config.ts` 已支持 `VITE_API_TARGET`（`front1` 的 P3 改动），可以显式指向 8000：

```bat
set VITE_API_TARGET=http://127.0.0.1:8000
npm run dev -- --port 5180 --strictPort
```

PowerShell：

```powershell
$env:VITE_API_TARGET="http://127.0.0.1:8000"
npm run dev -- --port 5180 --strictPort
```

如果分支的 `vite.config.ts` 还是写死 `8001`，**不要提交**修改，只在本地临时改成 `8000` 或 `8010`，验证完还原。

模式 A 的限制：你改的后端代码不会生效（8000 是主实例的进程，且未开 `--reload`）。需要改后端就走模式 B。

### 模式 B：前后端都自己起（需要改后端 / 跑后端测试）

#### B1. 复制数据，绝不共用

在**主工作区**执行一次快照（后端正在跑也能安全复制）：

```bat
cd /d D:\知枢星图\backend
.venv\Scripts\python.exe -c "import sqlite3; src=sqlite3.connect(r'data/knowledge.db'); dst=sqlite3.connect(r'D:\知枢星图-worktrees\<your-branch>\backend\data\knowledge.db'); src.backup(dst); dst.close(); src.close()"
```

复制 FAISS 索引（很小，约 68KB）：

```bat
xcopy /E /I /Y C:\temp\zhishuxingtu_faiss C:\temp\zhishuxingtu_faiss_<your-branch>
```

#### B2. 准备自己的 `.env`

worktree 里通常没有 `.env`（被 gitignore）。从主工作区复制一份，然后**只改这三个值**：

```bat
copy D:\知枢星图\backend\.env D:\知枢星图-worktrees\<your-branch>\backend\.env
```

```dotenv
# 用 worktree 自己的库（相对 backend 工作目录）
DATABASE_URL=sqlite:///./data/knowledge.db
# 关键：FAISS 必须独立，否则两个后端退出时互相覆盖
FAISS_INDEX_PATH=C:/temp/zhishuxingtu_faiss_<your-branch>
# 可选：Agent checkpoint 也建议独立（默认已是相对路径，确认不要指向主库）
AGENT_CHECKPOINT_DB=./data/langgraph_checkpoints.db
```

> `langgraph_checkpoints.db` 在主库有 400MB+，不要复制；用空的新文件即可（只影响 Agent 历史会话，不影响笔记）。

#### B3. Python 环境

优先复用主实例的 `.venv`（只读，不装包时安全）：

```bat
D:\知枢星图\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

如果分支改了依赖，或你要装包，就在自己的 worktree 建独立环境：

```bat
cd /d D:\知枢星图-worktrees\<your-branch>\backend
uv venv .venv --python F:\ANACONDA\python.exe --system-site-packages
.venv\Scripts\activate
uv pip install -r requirements.txt
```

> 本项目没有 `pyproject.toml` / `uv.lock`，不要用 `uv sync`；依赖清单是 `requirements.txt`。
> 主工作区的 `backend/venv` 是坏的（无 fastapi），不要用。

#### B4. 启动后端（8010）

```bat
cd /d D:\知枢星图-worktrees\<your-branch>\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

**如果启动卡在 import、1 分钟没有任何日志**：这台机器上 SQLAlchemy 会触发 Windows 平台探测（WMI）卡死。用下面这个启动器（放在你自己 worktree 的 `.workbuddy/dev_server.py`，不要提交）：

```python
import os
import platform
import sys

platform.win32_ver = lambda *a, **k: ("", "", "", "")
platform.machine = lambda: "AMD64"
sys.path.insert(0, os.getcwd())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8010)
```

```bat
cd /d D:\知枢星图-worktrees\<your-branch>\backend
.venv\Scripts\python.exe -u ..\.workbuddy\dev_server.py
```

注意：打了补丁就**不要加 `--reload`**，因为 reload 的子进程不会继承这个补丁；改后端后手动重启（约 35 秒）。

#### B5. 启动前端（5180 → 8010）

```bat
cd /d D:\知枢星图-worktrees\<your-branch>\frontend
npm install
set VITE_API_TARGET=http://127.0.0.1:8010
npm run dev -- --port 5180 --strictPort
```

PowerShell 用 `$env:VITE_API_TARGET="http://127.0.0.1:8010"`。

---

## 4. 启动后的自检

```bat
curl http://127.0.0.1:8010/health
curl http://localhost:5180/
```

登录拿 token（表单，不是 JSON）：

```bat
curl -X POST http://127.0.0.1:8010/api/auth/login ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "username=<user>&password=<pass>"
```

验证聚合接口（需要 P3 代码；没有该路由说明你的分支还没合并 P3，属正常）：

```bat
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8010/api/home/overview
```

前端代理是否通：

```bat
curl -H "Authorization: Bearer <token>" http://localhost:5180/api/home/overview
```

不同端口是不同 origin，`localStorage` 不共享，登录要重新来一次。

---

## 5. 冲突排查对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动报 `[Errno 10048]` | 端口被占 | `netstat -ano \| findstr :8010`，只 kill 自己的 PID |
| `database is locked` / 写入偶发失败 | 两个后端共用同一个 SQLite | 停掉自己的后端，按 B1 复制库后再起 |
| FAISS 报错、检索结果诡异、退出时卡住 | 两个后端共用 `C:/temp/zhishuxingtu_faiss` | 各自用 `..._<branch>` 独立目录 |
| 页面请求打到别人的数据 | 前端代理指到了 8000 | 检查 `VITE_API_TARGET` 和 Network 面板里的端口 |
| HMR 改 A 页面 B 页面变了 | 两个 Vite 共用同一目录/缓存 | 确认在各自 worktree、各自端口；不要共用 `node_modules` |
| 后端改了不生效 | 主实例没有 `--reload`，或你连的是 8000 | 改后端必须用自己的 8010 实例 |
| `ModuleNotFoundError: langgraph` | 用了 Anaconda 基础 Python | 用 `backend/.venv` 或自己 `uv venv` 装 `requirements.txt` |

---

## 6. Git 与数据卫生

- 只在 `D:\知枢星图-worktrees\<your-branch>` 里提交；**不要**在主工作区 `git stash` / `git reset` / `git checkout`。
- 不要提交：`backend/.env`、`backend/data/*.db`、`C:/temp` 下的索引、`docs/design/qa/**` 截图（除非明确要入库）。
- 合并前先 `git fetch`，在自己的 worktree 里 rebase/merge；主工作区的 `front1` 不会被你影响。
- 如果你在 `.claude/worktrees/main-agent-fix` 里工作：它已有自己的 `backend/data/knowledge.db`（308KB，和主库不是同一份）和 `.env`，但**没有 `frontend/node_modules`**；先 `npm install`，并把 `FAISS_INDEX_PATH` 改到独立目录。

---

## 7. 给你的最小执行清单

1. `git worktree add` 到独立目录，确认 `git branch --show-current` 是自己的分支
2. 检查 `8010` / `5180` 没被占用
3. 只改前端 → 模式 A；改后端 → 模式 B（复制 DB + FAISS、改三个 env）
4. 启动后端，`/health` 返回 200；启动前端，`5180` 可访问
5. 登录后验证 `/api/home/overview`（如果分支有 P3）与页面数据
6. 全程不碰 `8000` / `5173` 的进程，不在主工作区切分支
