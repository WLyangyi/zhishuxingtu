# 智能导入功能 - 实施计划

## 文档信息

| 项目 | 内容 |
|------|------|
| 产品名称 | 知枢星图 |
| 文档类型 | 实施计划 |
| 版本 | v1.0.0 |
| 创建日期 | 2026-04-09 |
| 基于设计文档 | 2026-04-09-import-design.md (v1.1.1) |

---

## 总体工作量

| 阶段 | 交付内容 | 预计工作量 |
|------|----------|------------|
| Phase 1 | 基础框架 + PDF 导入 | 2-3 天 |
| Phase 2 | 网页论文导入 + SSE 进度 | 1-2 天 |
| Phase 3 | 视频导入基础（字幕提取） | 1-2 天 |
| Phase 4 | Whisper 语音转文字集成 | 1-2 天 |
| Phase 5 | 在线视频支持（yt-dlp） | 1-2 天 |
| Phase 6 | 预览编辑 + 重新生成 | 1 天 |
| Phase 7 | 导入历史 + 分类建议 | 1 天 |
| Phase 8 | 测试 + 修复 + 文档 | 1-2 天 |

**总预计工作量**：9-15 天

---

## Phase 1：基础框架 + PDF 导入

### 1.1 后端基础架构

#### 1.1.1 创建导入相关模型
- [ ] 创建 `backend/app/models/import_history.py`
  - 定义 `ImportHistory` SQLAlchemy 模型
  - 包含字段：id, user_id, task_id, source_type, source_url, source_filename, duration, platform, generated_title, note_id, status, created_at

#### 1.1.2 创建导入任务内存存储
- [ ] 创建 `backend/app/services/import_task_store.py`
  - 定义 `ImportTask` 数据类
  - 实现任务存储（字典）和基本操作
  - 实现 `create_task()`, `get_task()`, `update_task()`, `delete_task()`

#### 1.1.3 创建 PDF 解析服务
- [ ] 创建 `backend/app/services/pdf_service.py`
  - 实现 `PDFService` 类
  - 实现 `extract_text(file_path, max_chars)` 方法
  - 实现错误处理：加密、扫描版、损坏、空文件
  - 依赖：`pymupdf`

#### 1.1.4 创建 AI 摘要服务
- [ ] 创建 `backend/app/services/summarizer_service.py`
  - 实现 `SummarizerService` 类
  - 实现 `summarize(content, source_type)` 方法
  - 实现 `suggest_category(summary, available_folders)` 方法
  - 实现超长内容分段处理
  - 复用现有的 LLM 服务

**AI 摘要生成详细规范：**

```
【标题生成规范】
- 根据内容主题生成 5-15 字的中文标题
- 标题应简洁明了，突出核心主题
- 避免使用"关于...的研究"、"...的分析"等通用开头
- 示例：「Attention Is All You Need 核心解读」而非「关于Transformer论文的分析」

【摘要生成规范】
- 长度：200-500 字
- 结构：
  1. 一句话概括核心主题（50字以内）
  2. 背景/问题：说明内容的背景或要解决的问题
  3. 核心内容：详细说明主要观点、方法、发现
  4. 价值/应用：内容的意义或实际应用场景
- 语言风格：正式书面语，客观陈述，避免主观评价
- 对于论文：重点说明创新点、实验结果、贡献
- 对于教程/博客：重点说明知识点、实操步骤、适用场景
- 对于视频：重点说明视频的核心话题、讨论要点、干货内容

【关键要点生成规范】
- 生成 3-8 个关键要点
- 每个要点 20-100 字
- 要点类型及占比：
  - 概念类（30%）：定义、原理、机制
  - 方法类（30%）：技术、算法、流程、步骤
  - 结论类（25%）：发现、结果、观点、规律
  - 应用类（15%）：场景、案例、实践、注意事项
- 每个要点使用「•」开头，言简意赅
- 避免重复，层次分明

【标签生成规范】
- 生成 3-8 个标签
- 标签类型及来源：
  - 主题标签：内容所属的领域/学科
  - 技术标签：涉及的技术、工具、框架
  - 场景标签：适用场景、使用条件
  - 格式标签：内容形式（论文/教程/视频等）
- 标签格式：2-6 字的中文词或英文词
- 示例：["机器学习", "深度学习", "Transformer", "NLP", "论文解读"]

【来源类型差异化处理】
- PDF/论文：侧重研究方法、实验数据、学术贡献
- 网页文章：侧重观点陈述、实用信息、时效性
- 视频内容：侧重口语化提炼、时间线重点、可操作性

【超长内容分段处理】
- 单段 > 2000 字时自动分段
- 分段策略：按 `---` → 标题 → 段落 自然边界切分
- 分段摘要后合并去重
- 优先保留开头、中间核心、结尾结论

【导入结果数据结构】
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "source_info": {
    "type": "pdf|web|video",
    "filename": "原始文件名.pdf",
    "url": "https://...",
    "platform": "youtube|bilibili|local",
    "duration": 3600,
    "size": 2097152
  },
  "extracted_content": {
    "full_text": "原始全文（最多50000字）",
    "text_length": 15000,
    "language": "zh|en|multi"
  },
  "ai_generated": {
    "title": "AI生成的标题（5-15字）",
    "summary": "AI生成的摘要（200-500字）",
    "key_points": [
      "要点1：概念/原理说明...",
      "要点2：方法/技术说明...",
      "要点3：结论/发现说明..."
    ],
    "tags": ["标签1", "标签2", "标签3"],
    "content_type": "论文|教程|博客|视频|文档|其他",
    "language_detected": "zh"
  },
  "category_suggestion": {
    "recommended_folder_id": "folder-uuid",
    "recommended_folder_path": "个人/编程学习/Python",
    "confidence_score": 0.85,
    "reasoning": "该内容涉及...",
    "alternatives": [...]
  },
  "processing_info": {
    "started_at": "2026-04-22T10:00:00Z",
    "completed_at": "2026-04-22T10:01:30Z",
    "processing_time_seconds": 90,
    "steps_completed": ["content_extraction", "ai_summarize", "tag_generation", "category_suggestion"]
  }
}
```
```

#### 1.1.5 创建导入历史服务
- [ ] 创建 `backend/app/services/import_history_service.py`
  - 实现 `ImportHistoryService` 类
  - 实现 `create_record()`, `get_history()`, `update_note_id()`

#### 1.1.6 创建导入 API 路由
- [ ] 创建 `backend/app/api/routes/import.py`
  - 实现 `POST /api/import/pdf` - 上传 PDF
  - 实现 `GET /api/import/:task_id` - 获取任务详情
  - 实现 `POST /api/import/save` - 保存为笔记
  - 实现 `GET /api/import/history` - 获取导入历史
  - 实现 `DELETE /api/import/:task_id` - 删除任务

### 1.2 前端基础架构

#### 1.2.1 创建类型定义
- [ ] 创建 `frontend/src/types/import.ts`
  - 定义 `ImportTask`, `ImportResult`, `SourceInfo` 类型
  - 定义 API 请求/响应类型

#### 1.2.2 创建 API 客户端
- [ ] 创建 `frontend/src/api/import.ts`
  - 实现 PDF 上传 API
  - 实现任务详情 API
  - 实现保存 API
  - 实现历史记录 API

#### 1.2.3 创建 Pinia Store
- [ ] 创建 `frontend/src/stores/import.ts`
  - 定义 `useImportStore`
  - 管理导入任务状态
  - 管理导入历史状态

#### 1.2.4 创建导入弹窗组件
- [ ] 创建 `frontend/src/views/ImportModal.vue`
  - 实现来源选择（PDF/网页/视频 Tab）
  - 实现 PDF 文件上传（拖拽 + 点击）
  - 实现文件大小/类型前端校验
  - 实现"开始导入"按钮

### 1.3 集成测试
- [ ] 测试 PDF 上传和解析
- [ ] 测试 AI 摘要生成
- [ ] 测试保存为笔记

---

## Phase 2：网页论文导入 + SSE 进度

### 2.1 后端实现

#### 2.1.1 创建网页内容提取服务
- [ ] 创建 `backend/app/services/crawler_service.py`
  - 实现 `CrawlerService` 类
  - 使用 `trafilatura` 提取网页正文
  - 实现 `extract_content(url, max_chars)` 方法
  - 实现错误处理：无法访问、无正文、超时

#### 2.1.2 实现 SSE 流式进度
- [ ] 在 `backend/app/api/routes/import.py` 添加 SSE 端点
  - 实现 `GET /api/import/status/:task_id`
  - 支持 SSE 流式推送进度消息
  - 消息格式：`{"type": "progress"/"completed"/"error", "progress": int, "message": str}`

#### 2.1.3 添加网页导入 API
- [ ] 在 `import.py` 添加网页导入端点
  - 实现 `POST /api/import/url` - 提交网页 URL

### 2.2 前端实现

#### 2.2.1 创建 SSE 客户端工具
- [ ] 创建/扩展 `frontend/src/utils/sse.ts`
  - 实现 SSE 连接和消息处理
  - 支持进度消息解析
  - 支持错误消息处理
  - 支持自动重连（最多 3 次）

#### 2.2.2 创建导入进度组件
- [ ] 创建 `frontend/src/views/ImportProcessing.vue`
  - 显示进度条
  - 显示当前步骤
  - 显示步骤列表（已完成/进行中/待处理）
  - 实现取消按钮

#### 2.2.3 更新 ImportModal
- [ ] 更新 `ImportModal.vue`
  - 添加网页链接输入表单
  - 添加来源切换逻辑
  - 集成 SSE 进度显示

### 2.3 集成测试
- [ ] 测试网页 URL 导入
- [ ] 测试 SSE 进度流式推送
- [ ] 测试错误处理和显示

---

## Phase 3：视频导入基础（字幕提取）

### 3.1 后端实现

#### 3.1.1 创建视频处理服务
- [ ] 创建 `backend/app/services/video_service.py`
  - 实现 `VideoService` 类
  - 实现 `get_video_info(file_path)` - 获取视频信息
  - 实现 `extract_audio(video_path, output_path)` - 提取音频
  - 实现 `has_audio_track(file_path)` - 检查音频轨道
  - 依赖：`ffmpeg-python`

#### 3.1.2 创建字幕提取服务
- [ ] 创建 `backend/app/services/subtitle_service.py`
  - 实现 `SubtitleService` 类
  - 实现 `extract_subtitles(video_path)` - 提取字幕
  - 支持内嵌字幕（SRT/ASS）
  - 实现字幕解析为时间戳+文本列表

#### 3.1.3 添加视频导入 API
- [ ] 在 `import.py` 添加视频导入端点
  - 实现 `POST /api/import/video` - 上传本地视频
  - 实现视频处理流程：解析 → 字幕提取 → AI 摘要
  - 实现 SSE 进度推送

### 3.2 前端实现

#### 3.2.1 更新 ImportModal
- [ ] 更新 `ImportModal.vue`
  - 添加视频 Tab（本地/在线切换）
  - 实现视频文件上传（拖拽 + 点击）
  - 实现文件大小/类型前端校验
  - 支持格式：MP4, MKV, AVI, MOV

#### 3.2.2 更新进度组件
- [ ] 更新 `ImportProcessing.vue`
  - 视频处理步骤显示
  - 字幕提取模式进度
  - Whisper 转录模式进度（带提示）

### 3.3 集成测试
- [ ] 测试本地视频上传和解析
- [ ] 测试字幕提取（有字幕/无字幕）
- [ ] 测试视频进度显示

---

## Phase 4：Whisper 语音转文字集成

### 4.1 后端实现

#### 4.1.1 创建 Whisper 服务
- [ ] 创建 `backend/app/services/whisper_service.py`
  - 实现 `WhisperService` 类
  - 实现 `transcribe(audio_path, language)` - 语音转文字
  - 模型加载和缓存
  - 支持中文、英文等多语言
  - 依赖：`faster-whisper`

#### 4.1.2 更新视频导入流程
- [ ] 更新 `import.py` 视频处理逻辑
  - 字幕提取失败时自动切换 Whisper
  - 实现 Whisper 转录进度推送
  - 长时间转录超时处理

#### 4.1.3 更新配置
- [ ] 更新 `backend/app/core/config.py`
  - 添加 `WHISPER_MODEL`, `WHISPER_DEVICE` 配置

### 4.2 前端实现

#### 4.2.1 更新进度组件
- [ ] 更新 `ImportProcessing.vue`
  - Whisper 转录进度显示
  - 长处理时间提示

### 4.3 系统依赖
- [ ] 确认 ffmpeg 已安装
- [ ] 确认 faster-whisper 已安装
- [ ] （可选）下载 Whisper 模型到本地

### 4.4 集成测试
- [ ] 测试 Whisper 中文转录
- [ ] 测试 Whisper 英文转录
- [ ] 测试无字幕视频自动转录
- [ ] 测试长视频转录性能

---

## Phase 5：在线视频支持（yt-dlp）

### 5.1 后端实现

#### 5.1.1 创建 yt-dlp 服务
- [ ] 创建 `backend/app/services/ytdlp_service.py`
  - 实现 `YTDLService` 类
  - 实现 `is_supported(url)` - 检查平台支持
  - 实现 `get_video_info(url)` - 获取视频信息
  - 实现 `download(url, output_dir)` - 下载视频/音频
  - 定义支持的平台列表
  - 依赖：`yt-dlp`

#### 5.1.2 添加在线视频导入 API
- [ ] 在 `import.py` 添加在线视频端点
  - 实现 `POST /api/import/video-url` - 提交视频 URL
  - 实现平台检测
  - 实现视频下载 + 处理流程

#### 5.1.3 添加平台支持查询 API
- [ ] 在 `import.py` 添加支持查询端点
  - 实现 `GET /api/import/capabilities` - 获取支持的平台列表

### 5.2 前端实现

#### 5.2.1 更新 ImportModal
- [ ] 更新 `ImportModal.vue`
  - 添加在线视频链接输入
  - 添加支持的视频平台提示
  - 集成平台检测逻辑

#### 5.2.2 更新结果预览组件
- [ ] 创建/更新 `frontend/src/views/ImportResult.vue`
  - 显示视频平台信息
  - 显示视频时长

### 5.3 集成测试
- [ ] 测试 YouTube 视频导入
- [ ] 测试 Bilibili 视频导入
- [ ] 测试抖音视频导入
- [ ] 测试不支持平台的错误处理

---

## Phase 6：预览编辑 + 重新生成

### 6.1 后端实现

#### 6.1.1 添加重新生成 API
- [ ] 在 `import.py` 添加重新生成端点
  - 实现 `POST /api/import/regenerate`
  - 复用已有的 AI 摘要生成逻辑
  - 返回新的摘要结果

#### 6.1.2 添加原始内容查看支持
- [ ] 更新任务详情返回
  - 在 `GET /api/import/:task_id` 中返回 `extracted_content`
  - 标记是否为原始内容

### 6.2 前端实现

#### 6.2.1 创建结果预览组件
- [ ] 创建 `frontend/src/views/ImportResult.vue`
  - 显示 AI 生成的标题/摘要/要点/标签
  - 显示来源信息（文件名/URL/时长/平台）
  - 可折叠的"原始内容"查看区域

#### 6.2.2 添加编辑功能
- [ ] 更新 `ImportResult.vue`
  - 标题可编辑
  - 摘要可编辑
  - 要点可编辑（添加/删除）
  - 标签可编辑（添加/删除）

#### 6.2.3 添加重新生成按钮
- [ ] 更新 `ImportResult.vue`
  - 每个字段旁边的"重新生成"按钮
  - 集成 `POST /api/import/regenerate` API
  - 刷新后显示新结果

#### 6.2.4 添加存储位置选择
- [ ] 更新 `ImportResult.vue`
  - 分类/文件夹选择器
  - AI 分类建议显示
  - "采纳建议"按钮

#### 6.2.5 添加保存功能
- [ ] 更新 `ImportResult.vue`
  - "保存为笔记"按钮
  - 集成 `POST /api/import/save` API
  - 保存成功后跳转或提示

### 6.3 集成测试
- [ ] 测试预览编辑
- [ ] 测试重新生成
- [ ] 测试保存为笔记
- [ ] 测试存储位置选择

---

## Phase 7：导入历史 + 分类建议

### 7.1 后端实现

#### 7.1.1 增强历史记录功能
- [ ] 更新 `import_history_service.py`
  - 支持分页查询
  - 支持按来源类型筛选
  - 支持搜索

#### 7.1.2 创建分类建议服务
- [ ] 在 `summarizer_service.py` 添加分类建议方法
  - 定义分类建议提示词
  - 实现 `suggest_category(summary, available_folders)` 方法
  - 返回推荐的文件夹 ID 和理由

**智能分类建议详细规范：**

```
【分类决策因素】
基于以下信息综合判断最优分类：
1. 内容主题分析（摘要、关键词、标签）
2. 内容类型判断（论文/教程/新闻/笔记等）
3. 来源判断（PDF/网页/视频）
4. 用户已有文件夹结构

【分类建议输出格式】
{
  "recommended_folder_id": "xxx-xxx-xxx",
  "recommended_folder_path": "个人/编程学习/Python",
  "confidence_score": 0.85,
  "reasoning": "该内容涉及Python编程和机器学习，适合放在「个人/编程学习」分类下",
  "alternatives": [
    {
      "folder_id": "yyy-yyy-yyy",
      "folder_path": "工作/技术文档",
      "confidence_score": 0.45,
      "reasoning": "如果作为工作参考资料，可考虑此分类"
    }
  ]
}

【置信度评分标准】
- 0.9-1.0：高度匹配，内容主题与分类高度一致
- 0.7-0.9：良好匹配，内容与分类相关
- 0.5-0.7：一般匹配，需要用户确认
- < 0.5：低匹配，建议用户手动选择

【分类建议提示词模板】
分析以下内容的主题和类型，为其推荐最合适的分类文件夹。

待分析内容：
- 标题：{title}
- 摘要：{summary}
- 关键词：{keywords}
- 标签：{tags}
- 内容类型：{content_type}
- 来源：{source_type}

可用文件夹列表：
{folder_list}

请根据内容主题、类型和用户需求，选择最合适的分类，并提供置信度和推理过程。
```

#### 7.1.3 更新保存 API
- [ ] 更新 `POST /api/import/save`
  - 添加分类建议字段
  - 保存后更新历史记录的 note_id

### 7.2 前端实现

#### 7.2.1 创建导入历史组件
- [ ] 创建 `frontend/src/views/ImportHistory.vue`
  - 历史记录列表
  - 按来源类型筛选
  - 搜索功能
  - 分页

#### 7.2.2 更新存储位置选择
- [ ] 更新存储选择器
  - 显示 AI 分类建议
  - "采纳建议"快速按钮

### 7.3 集成测试
- [ ] 测试导入历史显示
- [ ] 测试筛选和搜索
- [ ] 测试分类建议

---

## Phase 8：测试 + 修复 + 文档

### 8.1 单元测试

#### 8.1.1 后端测试
- [ ] PDF Service 测试
  - [ ] 正常解析
  - [ ] 加密 PDF
  - [ ] 扫描版 PDF
  - [ ] 空 PDF
  - [ ] 大文件
- [ ] Crawler Service 测试
  - [ ] 正常网页
  - [ ] 重定向
  - [ ] 登录页
  - [ ] 无内容页
  - [ ] 超时
- [ ] Video Service 测试
  - [ ] 正常视频
  - [ ] 无音频视频
  - [ ] 损坏视频
- [ ] Subtitle Service 测试
  - [ ] 内嵌字幕
  - [ ] 外挂字幕
  - [ ] 无字幕
- [ ] Whisper Service 测试
  - [ ] 中文音频
  - [ ] 英文音频
  - [ ] 低质量音频
  - [ ] 长音频
- [ ] YTDL Service 测试
  - [ ] YouTube
  - [ ] Bilibili
  - [ ] 抖音
  - [ ] 不支持平台

#### 8.1.2 前端测试
- [ ] 文件上传测试
- [ ] SSE 连接测试
- [ ] 编辑功能测试
- [ ] 保存功能测试

### 8.2 集成测试
- [ ] 完整 PDF 导入流程
- [ ] 完整网页导入流程
- [ ] 完整本地视频导入流程
- [ ] 完整在线视频导入流程
- [ ] 错误场景测试

### 8.3 手动测试
- [ ] 各种类型的 PDF（论文、技术文档、报告）
- [ ] 各种学术网站（arXiv、CNKI、知乎博客）
- [ ] 各种类型的视频（有字幕/无字幕、中文/英文/混合）
- [ ] 各种视频平台（YouTube、Bilibili、抖音、西瓜视频）
- [ ] 各种边界情况（超长文本、短视频、纯音频视频）

### 8.4 Bug 修复
- [ ] 根据测试发现修复 Bug
- [ ] 优化用户体验

### 8.5 文档更新
- [ ] 更新 README 或相关文档
- [ ] 更新 API 文档（如需要）
- [ ] 添加使用说明

---

## 附录

### A. 文件清单

#### 后端新建文件
```
backend/app/
├── api/routes/import.py              # 导入 API 路由
├── models/import_history.py          # 导入历史模型
└── services/
    ├── import_task_store.py         # 导入任务内存存储
    ├── pdf_service.py                # PDF 解析服务
    ├── crawler_service.py            # 网页内容提取服务
    ├── video_service.py              # 视频处理服务
    ├── subtitle_service.py            # 字幕提取服务
    ├── whisper_service.py            # Whisper 语音转文字服务
    ├── ytdlp_service.py             # yt-dlp 在线视频服务
    ├── summarizer_service.py         # AI 摘要生成服务
    └── import_history_service.py    # 导入历史服务
```

#### 前端新建文件
```
frontend/src/
├── views/
│   ├── ImportModal.vue               # 导入弹窗组件
│   ├── ImportProcessing.vue          # 导入进度组件
│   ├── ImportResult.vue              # 结果预览组件
│   └── ImportHistory.vue             # 导入历史组件
├── stores/import.ts                  # 导入状态管理
├── api/import.ts                     # 导入 API 客户端
└── types/import.ts                  # 导入相关类型定义
```

#### 后端修改文件
- `backend/app/api/routes/__init__.py` - 注册导入路由
- `backend/app/core/config.py` - 添加导入相关配置
- `backend/app/models/__init__.py` - 导出导入历史模型
- `backend/app/services/__init__.py` - 导出导入服务

#### 前端修改文件
- `frontend/src/router/index.ts` - 添加导入相关路由
- `frontend/src/stores/index.ts` - 注册导入 store
- `frontend/src/types/index.ts` - 导出导入类型
- `frontend/src/views/Home.vue` - 添加导入入口

### B. 依赖清单

#### Python 依赖
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
```

#### 系统依赖
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 ffmpeg 二进制并添加到 PATH
```

### C. 配置变量

#### 环境变量 (.env)
```env
# 导入功能配置
IMPORT_MAX_FILE_SIZE=209715200  # 200MB
IMPORT_MAX_CHARS=50000         # 最大处理字符数
IMPORT_TIMEOUT=300              # 处理超时（秒）
IMPORT_TEMP_DIR=./temp/imports # 临时文件目录

# Whisper 配置
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# yt-dlp 配置
YTDLP_CACHE_DIR=./temp/ytdlp
```

---

## 实施顺序建议

### 紧凑计划（9 天）

| 天数 | 任务 |
|------|------|
| Day 1 | Phase 1 - 基础架构 + PDF 导入 |
| Day 2 | Phase 2 - 网页导入 + SSE |
| Day 3 | Phase 3 - 视频基础 |
| Day 4 | Phase 4 - Whisper 集成 |
| Day 5 | Phase 5 - 在线视频 |
| Day 6 | Phase 6 - 预览编辑 |
| Day 7 | Phase 7 - 历史 + 分类建议 |
| Day 8-9 | Phase 8 - 测试 + 修复 |

### 宽松计划（15 天）

| 天数 | 任务 |
|------|------|
| Day 1-2 | Phase 1 - 基础架构 + PDF 导入 |
| Day 3-4 | Phase 2 - 网页导入 + SSE |
| Day 5-6 | Phase 3 - 视频基础 |
| Day 7-8 | Phase 4 - Whisper 集成 |
| Day 9-10 | Phase 5 - 在线视频 |
| Day 11-12 | Phase 6 - 预览编辑 |
| Day 13 | Phase 7 - 历史 + 分类建议 |
| Day 14-15 | Phase 8 - 测试 + 修复 |
