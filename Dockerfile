# 知枢星图后端镜像：FastAPI + LangGraph + FAISS
# 前端镜像见 frontend/Dockerfile，两者由 docker-compose.yml 编排。
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl 仅用于健康检查；libgomp1 是 faiss-cpu 的 OpenMP 运行时依赖（slim 镜像不自带）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 镜像用精简依赖(去掉 torch 系与本地转写/视频下载能力,详见该文件头注释)
COPY backend/requirements-docker.txt ./requirements.txt

# 直连 pypi.org 在本机会被中途掐断(RemoteDisconnected → pip 解析到半截 JSON 后崩),
# 故默认走国内镜像;可用 --build-arg PIP_INDEX_URL=... 覆盖。
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir --retries 10 --timeout 60 -i "$PIP_INDEX_URL" -r requirements.txt

COPY backend/app ./app
COPY backend/scripts ./scripts

# SQLite 库、FAISS 索引、checkpoint 都落在这里；compose 用 volume 挂载持久化
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
