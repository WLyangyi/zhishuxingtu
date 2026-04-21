# 知枢星图 - 智能导入功能设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 产品名称 | 知枢星图 |
| 文档类型 | 功能设计文档 |
| 版本 | v1.1.0 |
| 创建日期 | 2026-04-09 |
| 更新日期 | 2026-04-09 |
| 功能名称 | 智能导入 (Smart Import) |

---

## 1. 功能概述

### 1.1 背景

知枢星图 V4 规划中包含数据导入导出功能。本设计文档聚焦于**智能导入**功能，支持用户将外部内容（PDF 文档、网页论文、视频）导入为结构化的知识库笔记。

### 1.2 核心价值

- **一键提取**：从 PDF、网页或视频中智能提取关键信息
- **结构化摘要**：AI 自动生成标题、摘要、要点、标签
- **进度可见**：SSE 流式显示处理状态
- **用户可控**：预览确认 + 重新生成 + 分类建议

### 1.3 成功标准

- 用户可以在 3 步内完成一次导入
- PDF 导入成功率 > 95%（非扫描版）
- 网页论文导入成功率 > 90%
- 视频导入成功率 > 85%
- 用户满意度 > 80%

---

## 2. 功能范围

### 2.1 支持的导入来源

| 来源 | 格式 | 说明 |
|------|------|------|
| PDF 文件 | .pdf | ≤ 200MB，支持文本提取 |
| 网页链接 | URL | 支持学术论文、博客、技术文档 |
| 本地视频 | .mp4/.mkv/.avi/.mov | ≤ 200MB，支持字幕提取或语音转文字 |
| 在线视频 | URL | 支持 YouTube、Bilibili、抖音、西瓜视频、微博等主流平台 |

### 2.2 不支持的范围

- 扫描版 PDF（无法提取文字）
- 需要登录的网页/视频
- 受验证码保护的页面
- 非文本内容（纯图片 PDF）
- 无声音的视频（Whisper 需要音频轨道）
- 部分平台因反爬机制可能下载失败（如抖音部分视频）

### 2.3 平台支持说明

| 平台分类 | 平台列表 | 支持度 |
|---------|---------|--------|
| 国外主流 | YouTube, Twitter, Instagram, TikTok | ✅ 高 |
| 国内主流 | Bilibili, 抖音, 西瓜视频, 微博 | ⚠️ 中（受反爬影响） |
| 国内其他 | 小红书, 知乎, 爱奇艺, 腾讯视频, 优酷 | ⚠️ 中低 |
| 通用 | 其他支持 yt-dlp 的平台 | ✅ 可用 |

> **注意**：部分平台可能有反爬机制或水印，成功率因平台和政策而异。

### 2.4 输出格式

AI 生成**结构化摘要**：
- 标题：简洁准确的文档标题
- 摘要：100-200 字的内容摘要
- 要点：3-5 个关键要点
- 标签：3-5 个相关标签
- 来源：原始文件/链接信息 + 媒体时长

---

## 3. 用户流程

### 3.1 主流程

```
用户点击「导入」
    │
    ├─ 选择「PDF文件」→ 上传 PDF（前端子校验大小/类型）
    │
    ├─ 选择「网页链接」→ 输入 URL
    │
    └─ 选择「本地视频」→ 上传视频文件
        或
        选择「在线视频」→ 输入视频 URL
    │
    ▼
SSE 流式显示进度
    │
    ├─ [1] 正在解析文件...
    ├─ [2] 正在提取内容...
    ├─ [3] 正在分析内容...
    ├─ [4] 正在生成摘要...
    └─ [5] 完成！
    │
    ▼
预览确认页面
    │
    ├─ 查看原始提取内容（折叠）
    ├─ 编辑标题/摘要/要点/标签
    ├─ 选择存储位置（支持 AI 分类建议）
    └─ [重新生成] 或 [保存为笔记]
    │
    ▼
保存成功 → 记录到导入历史
```

### 3.2 视频处理流程

```
视频导入请求
    │
    ├─ 本地视频：直接进入处理
    │
    └─ 在线视频：
         │
         ▼
         ┌─────────────────────────────────┐
         │ 使用 yt-dlp 下载视频/提取音频   │
         └─────────────────────────────────┘
              │
              ▼
    ┌─────────────────────────────────┐
    │ 字幕提取优先级：                   │
    │ 1. 内嵌字幕（SRT/ASS）           │
    │ 2. 外挂字幕文件                   │
    │ 3. Whisper 语音转文字            │
    └─────────────────────────────────┘
              │
              ▼
         ┌─────────────────────────────────┐
         │ Whisper 转录（如果没有字幕）    │
         │ - 使用 faster-whisper（本地）    │
         │ - 支持中文、英文等语言          │
         └─────────────────────────────────┘
              │
              ▼
         ┌─────────────────────────────────┐
         │ 合并时间戳 + 转录文本            │
         └─────────────────────────────────┘
              │
              ▼
         AI 摘要生成（使用转录文本）
```

### 3.3 异常流程

| 场景 | 处理 |
|------|------|
| PDF/视频 过大 (>200MB) | 前端拦截，提示「文件超过 200MB」 |
| 非 PDF 文件 | 前端拦截，提示「仅支持 PDF 文件」 |
| 非视频文件 | 前端拦截，提示「仅支持 MP4/MKV/AVI/MOV 文件」 |
| URL 无法访问 | SSE 返回错误，提示「无法访问该网页」 |
| 无法提取正文 | SSE 返回错误，提示「无法提取网页内容」 |
| 扫描版 PDF | SSE 返回错误，提示「无法识别文字，可能是扫描版 PDF」 |
| 视频无音频轨道 | SSE 返回错误，提示「该视频没有音频轨道，无法转录」 |
| 视频平台不支持 | SSE 返回错误，提示「暂不支持该视频平台，请尝试下载后上传」 |
| AI 处理超时 | SSE 返回错误，提示「处理超时，请重试」 |
| 网络中断 | 前端自动重连 3 次，仍失败则提示用户 |

---

## 4. 技术架构

### 4.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3)                              │
│                                                                   │
│   ┌──────────────┐         ┌──────────────┐                     │
│   │ ImportModal  │         │ ImportResult │                     │
│   │  导入弹窗    │ ──────▶ │  结果预览    │                     │
│   └──────────────┘         └──────────────┘                     │
│           │                        │                              │
│           │ SSE 进度流              │ 确认保存                      │
│           ▼                        ▼                              │
│   ┌──────────────────────────────────────────┐                  │
│   │           ImportStore (Pinia)             │                  │
│   └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP + SSE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         后端 (FastAPI)                           │
│                                                                   │
│   ┌──────────────┐         ┌──────────────┐                     │
│   │ import.py    │         │ sse.py       │                     │
│   │  导入路由    │         │  流式进度    │                     │
│   └──────────────┘         └──────────────┘                     │
│           │                        │                              │
│           ▼                        │                              │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                      服务层                                │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│   │  │ pdf_service  │  │ video_svc    │  │crawler_svc   │   │  │
│   │  │ PDF 解析     │  │ 视频处理     │  │ 网页内容提取  │   │  │
│   │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│   │  ┌──────────────┐  ┌──────────────┐                    │  │
│   │  │ subtitle_svc │  │ whisper_svc  │                    │  │
│   │  │ 字幕提取     │  │ 语音转文字   │                    │  │
│   │  └──────────────┘  └──────────────┘                    │  │
│   │  ┌──────────────┐  ┌──────────────┐                    │  │
│   │  │yt_dlp_svc   │  │ summarizer   │                    │  │
│   │  │ 在线视频下载  │  │ AI 摘要生成   │                    │  │
│   │  └──────────────┘  └──────────────┘                    │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 目录结构

```
backend/app/
├── api/
│   └── routes/
│       └── import.py          # 导入相关路由
├── services/
│   ├── pdf_service.py         # PDF 解析服务
│   ├── video_service.py        # 视频处理服务
│   ├── subtitle_service.py     # 字幕提取服务
│   ├── whisper_service.py      # Whisper 语音转文字服务
│   ├── ytdlp_service.py       # yt-dlp 在线视频下载服务
│   ├── crawler_service.py      # 网页内容提取服务
│   ├── summarizer_service.py   # AI 摘要生成服务
│   └── import_history_service.py  # 导入历史服务
└── models/
    └── import_history.py       # 导入历史模型

frontend/src/
├── views/
│   ├── ImportModal.vue         # 导入弹窗组件
│   └── ImportResult.vue        # 结果预览组件
├── stores/
│   └── import.ts               # 导入状态管理
├── api/
│   └── import.ts               # 导入 API 客户端
└── types/
    └── import.ts               # 导入相关类型定义
```

---

## 5. API 设计

### 5.1 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/import/pdf` | 上传 PDF 文件，返回任务 ID |
| POST | `/api/import/url` | 提交网页 URL，返回任务 ID |
| POST | `/api/import/video` | 上传本地视频，返回任务 ID |
| POST | `/api/import/video-url` | 提交在线视频链接，返回任务 ID |
| GET | `/api/import/status/:task_id` | SSE 流式获取处理进度 |
| GET | `/api/import/:task_id` | 获取任务详情（结果） |
| POST | `/api/import/regenerate` | 重新生成摘要 |
| POST | `/api/import/save` | 保存为笔记 |
| DELETE | `/api/import/:task_id` | 取消/删除任务 |
| GET | `/api/import/history` | 获取导入历史 |
| GET | `/api/import/capabilities` | 获取支持的视频平台列表 |

### 5.2 请求/响应格式

**POST /api/import/pdf**
```json
// Request (multipart/form-data)
{
  "file": <PDF 文件>
}

// Response
{
  "success": true,
  "data": {
    "task_id": "uuid-string",
    "filename": "论文标题.pdf",
    "file_size": 1024000
  }
}
```

**POST /api/import/video**
```json
// Request (multipart/form-data)
{
  "file": <视频文件>
}

// Response
{
  "success": true,
  "data": {
    "task_id": "uuid-string",
    "filename": "视频标题.mp4",
    "file_size": 52428800
  }
}
```

**POST /api/import/video-url**
```json
// Request
{
  "url": "https://www.youtube.com/watch?v=..."
}

// Response
{
  "success": true,
  "data": {
    "task_id": "uuid-string",
    "url": "https://www.youtube.com/watch?v=...",
    "platform": "youtube",
    "title": "视频标题（如果能获取到）"
  }
}
```

**GET /api/import/status/:task_id (SSE)**
```json
// PDF/网页进度
data: {"type": "progress", "progress": 10, "message": "正在解析文件..."}
data: {"type": "progress", "progress": 30, "message": "正在提取内容..."}
data: {"type": "progress", "progress": 50, "message": "正在分析内容..."}
data: {"type": "progress", "progress": 80, "message": "正在生成摘要..."}
data: {"type": "completed", "progress": 100, "result": {...}}

// 视频进度（字幕模式）
data: {"type": "progress", "progress": 10, "message": "正在提取字幕..."}
data: {"type": "progress", "progress": 40, "message": "正在处理字幕..."}
data: {"type": "progress", "progress": 70, "message": "正在生成摘要..."}
data: {"type": "completed", "progress": 100, "result": {...}}

// 视频进度（Whisper 模式）
data: {"type": "progress", "progress": 10, "message": "正在下载视频..."}
data: {"type": "progress", "progress": 25, "message": "正在提取音频..."}
data: {"type": "progress", "progress": 40, "message": "正在转录音频（Whisper）..."}
data: {"type": "progress", "progress": 70, "message": "正在生成摘要..."}
data: {"type": "completed", "progress": 100, "result": {...}}

// 错误消息
data: {"type": "error", "code": "VIDEO_NO_AUDIO", "message": "该视频没有音频轨道，无法转录"}
```

**POST /api/import/save**
```json
// Request
{
  "task_id": "uuid-string",
  "folder_id": "目标文件夹ID",
  "title": "用户编辑后的标题",
  "summary": "用户编辑后的摘要",
  "key_points": ["要点1", "要点2", "要点3"],
  "tags": ["标签1", "标签2"]
}

// Response
{
  "success": true,
  "data": {
    "note_id": "新建笔记的ID"
  }
}
```

---

## 6. 数据模型

### 6.1 导入任务 (In-Memory)

```python
class ImportTask:
    task_id: str
    user_id: str
    source_type: str  # "pdf" | "url" | "video" | "video_url"
    source_path: str
    status: str  # "pending" | "parsing" | "extracting" | "analyzing" | "summarizing" | "completed" | "failed"
    progress: int  # 0-100
    progress_message: str
    extracted_content: str  # 原始提取的文本
    video_info: Optional[VideoInfo]  # 视频信息
    raw_html: str  # 仅 URL 类型
    result: ImportResult
    error: str
    created_at: datetime
    updated_at: datetime

class VideoInfo:
    duration: int  # 时长（秒）
    width: int
    height: int
    fps: float
    audio_tracks: int
    subtitle_tracks: int
    platform: Optional[str]  # youtube, bilibili, None

class ImportResult:
    title: str
    summary: str
    key_points: List[str]
    tags: List[str]
    source_info: SourceInfo

class SourceInfo:
    type: str  # "pdf" | "web" | "video" | "video_url"
    url: Optional[str]
    filename: Optional[str]
    duration: Optional[int]  # 视频时长（秒）
    platform: Optional[str]  # 视频平台
    imported_at: datetime
```

### 6.2 导入历史表 (Database)

```sql
CREATE TABLE import_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    source_type VARCHAR(20) NOT NULL,  -- 'pdf', 'url', 'video', 'video_url'
    source_url VARCHAR(1000),
    source_filename VARCHAR(500),
    duration INTEGER,  -- 视频时长（秒）
    platform VARCHAR(50),  -- 视频平台
    generated_title VARCHAR(500),
    note_id VARCHAR(36),  -- 保存后的笔记 ID
    status VARCHAR(20) NOT NULL,  -- 'completed', 'failed', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_import_history_user ON import_history(user_id, created_at DESC);
```

---

## 7. 服务设计

### 7.1 PDF 解析服务

**依赖**: `pymupdf` (fitz)

```python
class PDFService:
    def extract_text(self, file_path: str, max_chars: int = 50000) -> str:
        """提取 PDF 文本内容

        Args:
            file_path: PDF 文件路径
            max_chars: 最大提取字符数（避免超出 AI Token 限制）

        Returns:
            提取的文本内容

        Raises:
            PDFParseError: 解析失败时抛出
        """
        # 1. 打开 PDF
        # 2. 遍历每一页
        # 3. 提取文本
        # 4. 截断到 max_chars
        # 5. 返回文本
```

**错误处理**:
- 文件损坏 → `PDFParseError("文件损坏，无法解析")`
- 加密 PDF → `PDFParseError("PDF 已加密，请先解密")`
- 扫描版 PDF → `PDFParseError("无法识别文字，可能是扫描版 PDF")`
- 空 PDF → `PDFParseError("PDF 为空")`

### 7.2 视频处理服务

**依赖**: `ffmpeg-python`, `yt-dlp`, `faster-whisper`

```python
class VideoService:
    def get_video_info(self, file_path: str) -> VideoInfo:
        """获取视频信息

        Args:
            file_path: 视频文件路径

        Returns:
            VideoInfo 对象
        """

    def extract_audio(self, video_path: str, output_path: str) -> str:
        """提取音频轨道

        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径

        Returns:
            音频文件路径
        """

    def has_audio_track(self, file_path: str) -> bool:
        """检查视频是否有音频轨道"""
```

### 7.3 字幕提取服务

**依赖**: `ffmpeg`, `srt-to-json` (自定义)

```python
class SubtitleService:
    def extract_subtitles(self, video_path: str) -> List[Subtitle]:
        """提取视频字幕

        Returns:
            List[Subtitle] - 时间戳 + 文本列表

        Raises:
            SubtitleExtractError: 提取失败时抛出
        """
        # 1. 检查内嵌字幕轨道
        # 2. 提取 SRT/ASS 格式
        # 3. 解析为时间戳 + 文本
        # 4. 返回列表
```

### 7.4 Whisper 语音转文字服务

**依赖**: `faster-whisper`

```python
class WhisperService:
    def transcribe(self, audio_path: str, language: str = "auto") -> List[Subtitle]:
        """使用 Whisper 转录音频

        Args:
            audio_path: 音频文件路径
            language: 语言代码，auto 表示自动检测

        Returns:
            List[Subtitle] - 时间戳 + 文本列表

        Raises:
            WhisperError: 转录失败时抛出
        """
        # 1. 加载 Whisper 模型（首次调用时加载）
        # 2. 执行转录
        # 3. 返回带时间戳的文本片段
```

### 7.5 yt-dlp 在线视频服务

**依赖**: `yt-dlp`

```python
class YTDLService:
    SUPPORTED_PLATFORMS = [
        # 国外平台
        "youtube",      # YouTube
        "twitter",     # Twitter/X
        "instagram",    # Instagram
        "tiktok",      # TikTok (国际版)
        # 国内平台
        "bilibili",    # B站
        "douyin",      # 抖音
        "xiagua",      # 西瓜视频
        "weibo",       # 微博视频
        "xiaohongshu", # 小红书
        "zhihu",       # 知乎视频
        "iqiyi",       # 爱奇艺
        "tencent",     # 腾讯视频
        "youku",       # 优酷
        # ...
    ]

    def get_video_info(self, url: str) -> VideoInfo:
        """获取在线视频信息"""

    def download(self, url: str, output_dir: str) -> str:
        """下载视频/音频

        Returns:
            下载后的文件路径
        """

    def is_supported(self, url: str) -> bool:
        """检查是否支持该 URL"""
```

### 7.6 网页内容提取服务

**依赖**: `trafilatura`

```python
class CrawlerService:
    def extract_content(self, url: str, max_chars: int = 50000) -> Tuple[str, str]:
        """提取网页正文内容

        Args:
            url: 网页 URL
            max_chars: 最大提取字符数

        Returns:
            (标题, 正文内容)

        Raises:
            CrawlerError: 提取失败时抛出
        """
        # 1. 使用 trafilatura 提取
        # 2. 获取标题和正文
        # 3. 截断到 max_chars
        # 4. 返回
```

**错误处理**:
- URL 无法访问 → `CrawlerError("无法访问该网页，请检查 URL")`
- 无正文内容 → `CrawlerError("无法提取网页正文内容")`
- 超时 → `CrawlerError("网页加载超时，请重试")`

### 7.7 AI 摘要生成服务

**依赖**: 使用现有的 LLM 服务 (DashScope)

```python
class SummarizerService:
    def summarize(self, content: str, source_type: str) -> ImportResult:
        """生成结构化摘要

        Args:
            content: 文档/转录内容
            source_type: 来源类型 "pdf" | "url" | "video"

        Returns:
            ImportResult 结构化结果
        """
        # 1. 根据 source_type 选择提示词模板
        # 2. 构建提示词
        # 3. 调用 LLM
        # 4. 解析 JSON 结果
        # 5. 返回 ImportResult
```

**超长内容处理**:
```python
def summarize(self, content: str, max_chars: int = 50000):
    """分段处理超长内容"""
    if len(content) <= max_chars:
        return self._summarize_single(content)

    # 1. 将内容分成多个段落
    # 2. 对每个段落生成摘要
    # 3. 汇总各段落摘要，再次生成整体摘要
```

### 7.8 导入历史服务

```python
class ImportHistoryService:
    def create_record(self, user_id: str, task: ImportTask) -> ImportHistory:
        """创建导入记录"""

    def get_history(self, user_id: str, limit: int = 20) -> List[ImportHistory]:
        """获取用户的导入历史"""

    def update_note_id(self, history_id: str, note_id: str):
        """更新关联的笔记 ID"""
```

---

## 8. 前端设计

### 8.1 导入弹窗 (ImportModal.vue)

```
┌────────────────────────────────────────────────────────────┐
│  智能导入                                              ✕  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  选择导入来源：                                            │
│                                                            │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────┐│
│  │    📄 PDF文件    │ │    🔗 网页链接    │ │ 🎬 视频    ││
│  │                  │ │                  │ │            ││
│  │  点击上传 PDF   │ │  输入 URL       │ │ 上传/链接  ││
│  └──────────────────┘ └──────────────────┘ └────────────┘│
│                                                            │
│  ─────────────────────────────────────────────             │
│                                                            │
│  （选中 PDF 时显示）                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │  📎 论文标题.pdf                        1.2 MB    │   │
│  │                                                    │   │
│  │  拖拽其他 PDF 文件到此处替换，或 点击选择文件       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  （选中 URL 时显示）                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │  输入网页 URL                                       │   │
│  │  https://arxiv.org/abs/...                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  （选中视频时显示）                                        │
│  ┌────────────────────────────────────────────────────┐   │
│  │  [上传本地视频]        或        [输入视频链接]     │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │  🎬 拖拽视频文件到此处，或 点击选择文件      │  │   │
│  │  │  支持 MP4, MKV, AVI, MOV  最大 200MB      │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  │                                                    │   │
│  │  ───────────── 或 ─────────────                   │   │
│  │                                                    │   │
│  │  📺 输入视频链接                                   │   │
│  │  https://youtube.com/watch?v=...                │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  文件大小限制：200MB   支持格式：PDF, MP4, MKV, AVI, MOV   │
│                                                            │
│                                    [取消]  [开始导入]       │
└────────────────────────────────────────────────────────────┘
```

### 8.2 处理状态 (ImportProcessing.vue)

**PDF/网页版本**:
```
┌────────────────────────────────────────────────────────────┐
│  当前步骤：正在提取内容...                                  │
│                                                            │
│  • ✓ 解析文件完成                                         │
│  • → 正在提取内容...                                      │
│  • ○ 正在分析内容                                         │
│  • ○ 正在生成摘要                                         │
└────────────────────────────────────────────────────────────┘
```

**视频版本（字幕模式）**:
```
┌────────────────────────────────────────────────────────────┐
│  当前步骤：正在转录音频（Whisper）...                       │
│                                                            │
│  • ✓ 下载视频完成                                         │
│  • ✓ 提取音频完成                                         │
│  • → 正在转录音频（Whisper）...  35%                      │
│  • ○ 正在生成摘要                                         │
│                                                            │
│  💡 提示：Whisper 转录可能需要几分钟，请耐心等待           │
└────────────────────────────────────────────────────────────┘
```

### 8.3 结果预览 (ImportResult.vue)

```
┌────────────────────────────────────────────────────────────┐
│  导入预览                                                ✕  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  来源：🎬 Transformer论文讲解.mp4           时长：15:32     │
│  来源：📺 https://youtube.com/watch?v=...    平台：YouTube │
│                                              状态：✅ 完成  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ [▼ 查看原始转录内容]                                 │   │
│  │ ─────────────────────────────────────────────────  │   │
│  │ 00:00 今天我们来讨论 Transformer 架构...           │   │
│  │ 00:05 首先，Transformer 是 2017 年由 Google 提出... │   │
│  │ （原始转录文本，按时间顺序排列）                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ─────────────────────────────────────────────────         │
│                                                            │
│  📌 标题                                        [🔄 重新生成]│
│  ┌────────────────────────────────────────────────────┐   │
│  │ Transformer 架构详解：从原理到应用                   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  📝 摘要                                        [🔄 重新生成]│
│  ┌────────────────────────────────────────────────────┐   │
│  │ 本视频详细介绍了 Transformer 的核心组件，包括       │   │
│  │ Self-Attention、Multi-Head Attention 等...         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  📋 关键要点                                   [🔄 重新生成]│
│  ┌────────────────────────────────────────────────────┐   │
│  │ • Transformer 采用 Self-Attention 机制替代 RNN    │   │
│  │ • Multi-Head Attention 允许模型关注不同位置        │   │
│  │ • 位置编码（Positional Encoding）解决序列顺序问题  │   │
│  │ • BERT 和 GPT 基于 Transformer 取得了突破性成果   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  🏷️ 标签                                                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │ [深度学习] [NLP] [Transformer] [注意力机制]        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  📂 存储位置                                               │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 个人 ▶ 学习笔记 ▶ AI 视频                        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│                                    [取消]  [保存为笔记]     │
└────────────────────────────────────────────────────────────┘
```

### 8.4 导入历史 (ImportHistory.vue)

```
┌────────────────────────────────────────────────────────────┐
│  导入历史                                                ✕  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  🔍 搜索导入记录...                                        │
│  筛选：[全部] [PDF] [网页] [视频]                         │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 🎬 Transformer论文讲解        今天 14:30  时长15:32│   │
│  │    📺 youtube.com                  ✅ 已保存       │   │
│  ├────────────────────────────────────────────────────┤   │
│  │ 📄 基于深度学习的NLP研究        昨天 10:20         │   │
│  │    📎 论文.pdf                        ✅ 已保存   │   │
│  ├────────────────────────────────────────────────────┤   │
│  │ 🔗 Attention Is All You Need       04-07          │   │
│  │    https://arxiv.org/abs/...       ✅ 已保存       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  共 45 条记录                          [< 1 2 3 ... 5 >]  │
└────────────────────────────────────────────────────────────┘
```

---

## 9. AI 提示词设计

### 9.1 论文摘要生成提示词

```json
{
  "name": "论文摘要生成",
  "category": "import",
  "is_system": true,
  "system_prompt": "你是一个学术论文分析助手。你擅长从学术论文中提取关键信息，生成简洁准确的结构化摘要。",
  "user_prompt_template": "请分析以下论文内容，生成结构化摘要。\n\n论文内容：\n{content}\n\n要求：\n1. 标题要概括文档核心主题，不超过50字\n2. 摘要要包含研究目的、方法、结论，100-200字\n3. 要点提取3-5个最重要的信息，每个不超过50字\n4. 标签反映学术领域和技术关键词\n\n以JSON格式返回：\n{{\n  \"title\": \"标题\",\n  \"summary\": \"摘要\",\n  \"key_points\": [\"要点1\", \"要点2\", \"要点3\", \"要点4\", \"要点5\"],\n  \"tags\": [\"标签1\", \"标签2\", \"标签3\", \"标签4\", \"标签5\"]\n}}",
  "output_format": "JSON",
  "variables": ["content"]
}
```

### 9.2 视频摘要生成提示词

```json
{
  "name": "视频摘要生成",
  "category": "import",
  "is_system": true,
  "system_prompt": "你是一个视频内容分析助手。你擅长从视频转录文本中提取关键信息，生成简洁准确的结构化摘要。注意视频内容的口语化特点。",
  "user_prompt_template": "请分析以下视频转录内容，生成结构化摘要。\n\n视频转录：\n{content}\n\n要求：\n1. 标题要概括视频核心主题，不超过50字\n2. 摘要要概括视频的主要内容、观点和结论，100-200字\n3. 要点提取3-5个视频中最重要的知识点或讨论点\n4. 标签反映视频的主题领域和关键词\n\n以JSON格式返回：\n{{\n  \"title\": \"标题\",\n  \"summary\": \"摘要\",\n  \"key_points\": [\"要点1\", \"要点2\", \"要点3\", \"要点4\", \"要点5\"],\n  \"tags\": [\"标签1\", \"标签2\", \"标签3\", \"标签4\", \"标签5\"]\n}}",
  "output_format": "JSON",
  "variables": ["content"]
}
```

### 9.3 分类建议提示词

```json
{
  "name": "分类建议",
  "category": "import",
  "is_system": true,
  "system_prompt": "你是一个知识管理助手。你擅长根据文档内容推荐合适的存储位置。",
  "user_prompt_template": "根据以下内容，推荐最合适的分类和文件夹。\n\n内容摘要：\n{summary}\n\n可用分类：\n{categories}\n\n请分析内容主题，返回最合适的分类路径。\n\n以JSON格式返回：\n{{\n  \"recommended_folder_id\": \"文件夹ID\",\n  \"reason\": \"推荐理由\"\n}}"
}
```

---

## 10. 配置参数

### 10.1 环境变量

```env
# 导入功能配置
IMPORT_MAX_FILE_SIZE=209715200  # 200MB
IMPORT_MAX_CHARS=50000         # 最大处理字符数
IMPORT_TIMEOUT=300              # 处理超时（秒）- 视频较长
IMPORT_TEMP_DIR=./temp/imports  # 临时文件目录

# Whisper 配置
WHISPER_MODEL=base  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu   # cpu, cuda
WHISPER_COMPUTE_TYPE=int8  # int8, float16, float32

# yt-dlp 配置
YTDLP_CACHE_DIR=./temp/ytdlp
YTDLP_MAX_FILESIZE=209715200  # 200MB
```

### 10.2 后端配置

```python
# backend/app/core/config.py

class ImportConfig:
    MAX_FILE_SIZE: int = 200 * 1024 * 1024  # 200MB
    MAX_CHARS: int = 50000
    TIMEOUT: int = 300  # 5分钟，视频处理较长
    TEMP_DIR: str = "./temp/imports"
    SUPPORTED_PDF_TYPES = ["application/pdf"]
    SUPPORTED_VIDEO_TYPES = [
        "video/mp4",
        "video/x-matroska",  # mkv
        "video/x-msvideo",    # avi
        "video/quicktime"     # mov
    ]
    SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov"]
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    YTDLP_CACHE_DIR: str = "./temp/ytdlp"
```

---

## 11. 错误处理

### 11.1 错误类型

| 错误码 | 错误信息 | 处理方式 |
|--------|----------|----------|
| `IMPORT_FILE_TOO_LARGE` | 文件超过 200MB 限制 | 前端拦截 |
| `IMPORT_INVALID_TYPE` | 不支持的文件类型 | 前端拦截 |
| `IMPORT_PDF_ENCRYPTED` | PDF 已加密 | SSE 错误 |
| `IMPORT_PDF_SCANNED` | 无法识别文字，可能是扫描版 | SSE 错误 |
| `IMPORT_PDF_CORRUPT` | PDF 文件损坏 | SSE 错误 |
| `IMPORT_URL_UNREACHABLE` | 无法访问该网页 | SSE 错误 |
| `IMPORT_URL_TIMEOUT` | 网页加载超时 | SSE 错误 |
| `IMPORT_CONTENT_EXTRACT_FAILED` | 无法提取网页正文 | SSE 错误 |
| `IMPORT_VIDEO_NO_AUDIO` | 该视频没有音频轨道，无法转录 | SSE 错误 |
| `IMPORT_VIDEO_UNSUPPORTED` | 暂不支持该视频平台 | SSE 错误 |
| `IMPORT_VIDEO_DOWNLOAD_FAILED` | 视频下载失败 | SSE 错误 |
| `IMPORT_VIDEO_SUBTITLE_FAILED` | 字幕提取失败，尝试转录 | SSE 警告后自动转录 |
| `IMPORT_WHISPER_FAILED` | 语音转文字失败 | SSE 错误 |
| `IMPORT_AI_TIMEOUT` | AI 处理超时 | SSE 错误 |
| `IMPORT_AI_FAILED` | AI 生成摘要失败 | SSE 错误 |
| `IMPORT_FOLDER_NOT_FOUND` | 目标文件夹不存在 | 保存时校验 |
| `IMPORT_SAVE_FAILED` | 保存笔记失败 | 保存时错误 |

### 11.2 SSE 错误格式

```json
data: {"type": "error", "code": "VIDEO_NO_AUDIO", "message": "该视频没有音频轨道，无法转录"}

data: {"type": "warning", "code": "SUBTITLE_EXTRACT_FAILED", "message": "字幕提取失败，将使用 Whisper 转录"}

data: {"type": "progress", "progress": 45, "message": "正在使用 Whisper 转录..."}
```

---

## 12. 安全考虑

### 12.1 文件上传安全

- 文件大小校验：前端 + 后端双重校验
- 文件类型校验：检查 MIME type 和扩展名
- 临时文件：处理完成后立即删除
- 路径遍历防护：生成随机文件名

### 12.2 URL 访问安全

- URL 白名单：仅允许 http/https
- 请求超时：30 秒（网页）/ 60 秒（视频下载）
- 重定向限制：网页不跟随超过 3 次，视频下载不跟随超过 5 次
- 恶意 URL 检测：检查域名是否在黑名单
- 视频平台限制：仅允许预定义的平台列表

### 12.3 内容安全

- 敏感信息过滤：使用现有的敏感词过滤
- 免责声明：保存时追加来源信息
- 视频内容审核：无（用户自有内容）

---

## 13. 性能考虑

### 13.1 限流

- 单用户并发导入任务：最多 1 个
- 单个文件大小：≤ 200MB
- 每小时导入次数限制：30 次（可配置）
- 视频转录：使用 Whisper 本地推理，无 API 限制

### 13.2 缓存

- 已导入的 URL：24 小时内不重复抓取（基于 URL hash）
- AI 摘要结果：失败重试时使用相同内容，不重新解析/转录
- Whisper 模型：首次加载后缓存到内存

### 13.3 异步处理

- PDF 解析：同步处理（文件已在服务器）
- 网页抓取：同步处理（需要等待网络响应）
- 视频下载：同步处理（yt-dlp 支持进度回调）
- 视频转录：同步处理（Whisper 本地推理）
- AI 生成：同步处理（流式返回）

### 13.4 临时文件管理

```
temp/
└── imports/
    ├── pdf_abc123.pdf
    ├── video_def456.mp4
    ├── audio_ghi789.wav
    └── ...
```

- 临时文件在任务完成后自动删除
- 启动时清理过期临时文件（> 24 小时）

---

## 14. 测试计划

### 14.1 单元测试

| 模块 | 测试内容 |
|------|----------|
| PDF Service | 正常解析、加密 PDF、扫描版 PDF、空 PDF、大文件 |
| Video Service | 正常视频、无音频视频、损坏视频 |
| Subtitle Service | 内嵌字幕、外挂字幕、无字幕 |
| Whisper Service | 中文音频、英文音频、低质量音频、长音频 |
| YTDL Service | YouTube、Bilibili、抖音等平台、不支持平台 |
| Crawler Service | 正常网页、重定向、登录页、无内容页、超时 |
| Summarizer Service | 正常内容、超长内容、特殊字符、JSON 解析错误 |

### 14.2 集成测试

| 场景 | 预期结果 |
|------|----------|
| 上传有效 PDF | 成功生成摘要 |
| 输入有效 URL | 成功生成摘要 |
| 上传本地视频 | 成功生成摘要（字幕或 Whisper） |
| 输入在线视频 URL | 成功下载并生成摘要 |
| 上传 > 200MB 文件 | 拒绝上传 |
| 输入无效 URL | 返回错误 |
| 上传无音频视频 | 返回错误提示 |
| 保存为笔记 | 笔记创建成功 |

### 14.3 手动测试

- 各种类型的 PDF（论文、技术文档、报告）
- 各种学术网站（arXiv、CNKI、知乎博客）
- 各种类型的视频（有字幕/无字幕、中文/英文/混合）
- 各种视频平台（YouTube、Bilibili、抖音、西瓜视频）
- 各种边界情况（超长文本、短视频、纯音频视频）

---

## 15. 里程碑

| 阶段 | 交付内容 | 预计工作量 |
|------|----------|------------|
| Phase 1 | 基础框架 + PDF 导入 + 简单摘要 | 2-3 天 |
| Phase 2 | 网页论文导入 + SSE 进度 | 1-2 天 |
| Phase 3 | 视频导入基础（字幕提取） | 1-2 天 |
| Phase 4 | Whisper 语音转文字集成 | 1-2 天 |
| Phase 5 | 在线视频支持（yt-dlp） | 1-2 天 |
| Phase 6 | 预览编辑 + 重新生成 | 1 天 |
| Phase 7 | 导入历史 + 分类建议 | 1 天 |
| Phase 8 | 测试 + 修复 + 文档 | 1-2 天 |

**总预计工作量**：9-15 天

---

## 16. 依赖清单

### 16.1 Python 依赖

```txt
# PDF 处理
pymupdf>=1.23.0

# 视频处理
ffmpeg-python>=0.2.0

# 在线视频
yt-dlp>=2024.0.0

# 语音转文字
faster-whisper>=0.10.0

# 网页抓取
trafilatura>=1.6.0

# 异步处理（如需要）
aiofiles>=23.0.0
```

### 16.2 系统依赖

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 ffmpeg 二进制并添加到 PATH
```

---

## 17. 文档历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0.0 | 2026-04-09 | 初始版本，定义 PDF 和网页导入功能 |
| v1.1.0 | 2026-04-09 | 新增视频导入功能，支持本地视频和在线视频 |
| v1.1.1 | 2026-04-09 | 明确支持抖音等国内视频平台，增加平台支持说明表 |
