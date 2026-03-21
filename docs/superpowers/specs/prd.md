# 知枢星图 - 个人知识库系统 PRD

## 文档信息

| 项目 | 内容 |
|------|------|
| 产品名称 | 知枢星图 |
| 版本 | v1.8.0 |
| 文档状态 | 已确认 |
| 创建日期 | 2026-03-17 |
| 最后更新 | 2026-03-20 |
| 作者 | 产品团队 |

---

## 1. 产品概述

### 1.1 背景

在信息爆炸的时代，个人知识管理变得越来越重要。用户每天接触大量的信息资源，包括文章、博客、视频、开源项目等，但缺乏一个有效的工具来整合、组织和利用这些知识。现有的知识管理工具要么功能过于复杂，要么缺乏智能化的辅助功能。

### 1.2 价值主张

知枢星图是一个现代化的个人知识库系统，旨在帮助用户：

1. **整合知识资源** - 统一管理各类知识资源（文本笔记、链接、文件等）
2. **建立知识关联** - 通过双向链接和知识图谱，建立知识之间的联系
3. **智能辅助学习** - 利用 AI 技术提供智能问答和知识检索
4. **高效组织管理** - 通过文件夹、标签、链接等多种方式组织知识

### 1.2.1 产品愿景（升级版）

知枢星图不仅是一个笔记管理工具，更是一个**个人知识资产管理平台**：

**首页设计：**
- 三个主入口：个人 (Personal)、工作 (Work)、素材 (Assets)
- 极简设计，每个入口清晰明了

**内容分类体系：**
- **个人** - 笔记、日记、简历等个人成长相关内容
  - 支持 4 层嵌套文件夹结构
  - 内置 AI 助手、智能检索、知识图谱功能
- **工作** - 项目文档、任务列表、里程碑等职业发展内容
  - 按项目组织，支持多种内容类型
- **素材** - 图片、附件、链接收藏等创作资源
  - 支持本地上传和外部链接

**主页入口结构：**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    个人     │    │    工作     │    │    素材     │
│   Personal  │    │    Work     │    │   Assets    │
└─────────────┘    └─────────────┘    └─────────────┘
```

**「个人」入口结构：**
```
个人
├── 📁 笔记文件夹（支持 4 层嵌套）
├── 🔍 智能检索
├── 🔗 知识图谱
└── 🤖 AI 助手
```

**Skill 智能模块：**
- 可执行的智能模块，类似 AI Agent 技能包
- 支持用户手动创建、系统预设模板、AI 自动生成
- 与知识库双向关联，执行结果可存回知识库
- 示例：对话总结 Skill、每日资讯 Skill、简历管理 Skill 等

### 1.3 目标用户

- **主要用户：** 个人知识工作者、学习者、研究人员
- **使用场景：** 
  - 学习新知识时的笔记整理
  - 研究项目的资料收集和整理
  - 个人知识库的长期积累和管理
  - 知识的快速检索和回顾

### 1.4 业务目标

**MVP 阶段目标：**
- 完成核心功能开发，实现可用的个人知识库系统
- 支持基础的笔记管理、知识关联和智能问答
- 为后续功能扩展奠定良好的技术基础

**长期目标：**
- 成为用户信赖的个人知识管理工具
- 支持多平台访问和协作
- 持续优化 AI 辅助功能

---

## 2. 核心功能

### 2.1 功能列表

#### MVP 核心功能（V1）

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| 用户认证 | 简单的单用户登录认证系统 | P0 |
| 笔记管理 | 创建、编辑、删除、查看笔记 | P0 |
| Markdown 编辑器 | 分屏预览的 Markdown 编辑器 | P0 |
| 文件夹管理 | 2 层文件夹结构组织笔记 | P0 |
| 标签系统 | 扁平化标签管理 | P0 |
| 双向链接 | `[[笔记标题]]` 语法创建链接 | P0 |
| 反向链接 | 显示哪些笔记链接了当前笔记 | P0 |
| 全文搜索 | 基于标题和内容的搜索 | P0 |
| 知识图谱 | 全局和局部图谱可视化 | P0 |
| AI 问答 | 基于知识库的 RAG 智能问答 | P0 |

#### V2 功能（内容分类升级）

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| 主页3入口 | 个人/工作/素材三大分类入口，极简设计 | P0 |
| 文件夹4层嵌套 | 文件夹层级从2层扩展至4层，支持更自由的组织 | P0 |
| 内容分类体系 | 预设三大分类（个人/工作/素材）+ 用户自定义分类 | P1 |
| 内容类型管理 | 用户可自定义内容类型（日记、简历、业务知识等） | P1 |
| 素材管理 | 图片、链接、视频等素材管理（混合存储模式） | P1 |
| 分类视图 | 按分类浏览和筛选内容 | P1 |
| 内容类型模板 | 不同内容类型支持不同的字段模板 | P1 |
| AI助手集成 | 作为「个人」入口内的功能模块，支持对话和笔记联动 | P1 |

#### V3 功能（Skill 智能模块）

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| Skill 创建 | 用户手动创建和配置 Skill | P1 |
| Skill 模板库 | 系统预设常用 Skill 模板 | P1 |
| Skill 执行引擎 | 支持手动调用和定时自动执行 | P1 |
| AI 生成 Skill | AI 根据内容自动生成 Skill | P2 |
| Skill 与知识库关联 | Skill 执行结果存回知识库 | P1 |
| 对话总结 Skill | 自动总结对话内容并归档 | P2 |
| 每日资讯 Skill | 定时汇总资讯并归档 | P2 |
| 简历管理 Skill | 简历解析、面试题生成等 | P2 |

#### V3.1 功能（提示词工程）✅ 新增

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| 提示词管理 | 提示词的 CRUD 操作，支持系统预设和用户自定义 | P1 |
| 敏感词过滤 | 自动检测并过滤输入内容中的敏感词 | P1 |
| 免责声明 | AI 回复自动追加免责声明 | P1 |
| 提示词模板 | 系统预设 6 个常用提示词模板 | P1 |

#### V3.2 功能（向量长期记忆）✅ 新增

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| 对话向量化存储 | 将用户问题和AI回答向量化存储到 FAISS | P1 |
| 语义检索历史 | 基于当前问题语义检索相关历史对话 | P1 |
| 长期记忆 | 突破轮数限制，支持无限对话历史 | P1 |
| 跨会话记忆 | 不同对话间共享相关记忆 | P2 |
| "上次说的那个" | 支持引用历史对话中的内容 | P2 |

#### V3.3 功能（提示词工程进阶）✅ 新增

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| Few-Shot示例库 | 为三个核心场景提供示例库（对话总结、资料提取、知识库问答） | P1 |
| A/B测试框架 | 提示词版本管理、流量分配、实验控制 | P1 |
| CoT思维链模板 | 三种思维链模板（step_by_step, compare_analyze, deep_reasoning） | P1 |
| 效果评估系统 | 相关性、准确性、完整性、清晰度四维自动评估 | P1 |
| 提示词链编排 | 多步骤任务编排，支持链式调用 | P2 |
| 可视化编排界面 | 拖拽式流程设计 | P2 |

#### V3.4 功能（Reranker重排序）✅ 新增

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|--------|
| Cross-Encoder精排 | 使用阿里云gte-rerank模型对检索结果进行精细排序 | P1 |
| 候选集召回 | 先用向量检索召回Top-15候选，再用Reranker精排Top-5 | P1 |
| 对比测试API | 提供重排序前后效果对比接口 | P1 |
| 优雅降级 | Reranker不可用时自动使用原始分数排序 | P1 |
| 检索精度提升 | 通常能提升检索效果20-30% | P1 |

#### V3.5 功能（SSE流式输出）✅ 已实现

| 功能模块 | 状态 | 功能描述 | 优先级 |
|---------|------|---------|--------|
| SSE实时推送 | ✅ | 使用Server-Sent Events实现流式响应 | P1 |
| 逐字输出 | ✅ | AI回答逐字/逐句实时显示，提升用户体验 | P1 |
| 打字机效果 | ✅ | TypewriterText.vue组件实现打字机动画效果 | P1 |
| 停止生成 | ✅ | AbortController中断流式传输，节省Token消耗 | P1 |
| 相关笔记显示 | ✅ | 流式输出结束后显示来源笔记 | P1 |
| 首字响应优化 | ✅ | 首字响应时间从5-10秒降至<1秒 | P1 |

**SSE流式输出用户故事：**

- 作为用户，我想要看到AI回答逐字显示，以便减少等待焦虑
- 作为用户，我想要在AI回答过程中停止生成，以便节省时间
- 作为用户，我想要看到实时的Markdown渲染效果，以便更好地理解回答内容
- 作为用户，我想要在网络不稳定时自动重连，以便不丢失已生成的内容

**SSE流式输出验收标准：**

| 验收项 | 验收标准 |
|--------|----------|
| 首字响应时间 | < 1秒开始显示第一个字符 |
| 流式延迟 | 每个字符显示延迟 < 100ms |
| 打字机效果 | 光标闪烁动画流畅，无明显卡顿 |
| Markdown渲染 | 实时正确渲染标题、列表、代码块等 |
| 停止生成 | 点击后立即停止，不继续消耗Token |
| 错误重连 | 网络中断后自动重连最多3次 |
| 连接稳定性 | 正常网络下连接成功率 > 99% |

**Few-Shot示例场景：**

| 场景 | 输入示例 | 输出示例 |
|------|---------|---------|
| 对话总结 | 用户对话记录... | 结构化总结（主题、要点、待办） |
| 资料提取 | 外部文章内容... | 核心知识点、关键技术点、应用场景 |
| 知识库问答 | 问题 + 知识库内容 | 推理过程 + 对比分析 + 建议 |

**CoT思维链模板：**

| 模板类型 | 适用场景 | 特点 |
|---------|---------|------|
| step_by_step | 复杂问题分析 | 分步骤推理，逻辑清晰 |
| compare_analyze | 对比类问题 | 维度识别、对比分析、综合评估 |
| deep_reasoning | 深度推理问题 | 问题分解、假设验证、结论推导 |

**评估指标体系：**

| 指标类型 | 指标名称 | 评分范围 |
|---------|---------|---------|
| 质量指标 | 相关性评分 | 1-10分 |
| 质量指标 | 准确性评分 | 1-10分 |
| 质量指标 | 完整性评分 | 1-10分 |
| 质量指标 | 清晰度评分 | 1-10分 |
| 性能指标 | 响应时间 | 毫秒 |
| 性能指标 | Token使用量 | 数量 |
| 用户反馈 | 用户评分 | 1-5星 |

**实施计划：**

| 阶段 | 时间 | 交付物 |
|------|------|--------|
| Phase 1 | 2-3天 | Few-Shot示例库 + A/B测试基础 |
| Phase 2 | 3-4天 | CoT模板引擎 + 效果评估系统 |
| Phase 3 | 3-5天 | 提示词链编排引擎 |

#### V4 功能（部分完成）

| 功能模块 | 功能描述 | 优先级 | 状态 |
|---------|---------|--------|------|
| 语义搜索 | 基于向量的语义搜索 | P1 | ✅ 已完成 |
| 数据导入导出 | Markdown/JSON 格式导入导出 | P1 | ⏳ 待实现 |
| 批量导入 | 批量导入现有知识库 | P1 | ⏳ 待实现 |
| 网页内容提取 | 自动提取网页正文 | P1 | ⏳ 待实现 |
| 视频字幕分析 | 提取视频字幕进行内容分析 | P1 | ⏳ 待实现 |
| 浏览器插件 | 一键保存网页内容 | P2 | ⏳ 待实现 |

### 2.2 用户故事

**笔记管理：**
- 作为用户，我想要创建和编辑 Markdown 笔记，以便记录我的知识
- 作为用户，我想要通过文件夹和标签组织笔记，以便高效管理知识
- 作为用户，我想要在笔记之间创建链接，以便建立知识关联

**知识检索：**
- 作为用户，我想要通过关键词搜索笔记，以便快速找到所需知识
- 作为用户，我想要向 AI 提问并基于我的知识库获得答案，以便高效获取信息
- 作为用户，我想要查看知识图谱，以便直观了解知识之间的关联

**知识关联：**
- 作为用户，我想要看到哪些笔记链接了当前笔记，以便了解知识的引用关系
- 作为用户，我想要通过局部图谱查看当前笔记的关联网络，以便深入探索相关知识

### 2.3 使用场景

**场景 1：学习笔记整理**
1. 用户创建一个文件夹「AI 学习」
2. 在文件夹中创建多个笔记，记录学习内容
3. 使用标签「机器学习」「深度学习」分类笔记
4. 在笔记之间创建双向链接，建立知识关联
5. 通过知识图谱查看学习路径

**场景 2：知识检索**
1. 用户需要查找某个知识点
2. 在搜索框输入关键词或自然语言问题
3. 系统返回相关笔记列表或 AI 生成的答案
4. 用户点击笔记查看详细内容

**场景 3：知识关联探索**
1. 用户正在阅读一篇笔记
2. 展开右侧面板查看局部知识图谱
3. 发现相关的笔记并点击跳转
4. 查看反向链接，了解哪些笔记引用了当前笔记

---

## 3. 用户流程

### 3.1 用户旅程地图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   登录系统   │ -> │  创建/编辑   │ -> │  组织管理    │ -> │  检索使用    │
│             │    │    笔记     │    │  知识       │    │  知识       │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                   │                   │                   │
      v                   v                   v                   v
 - 输入用户名密码    - Markdown 编辑     - 文件夹分类        - 全文搜索
 - 进入主界面       - 分屏预览         - 标签管理          - AI 问答
                   - 保存笔记         - 双向链接          - 知识图谱
                                      - 查看关联
```

### 3.2 核心流程图

**笔记创建流程：**
```
用户点击「新建笔记」
    ↓
选择文件夹位置（可选）
    ↓
进入 Markdown 编辑器
    ↓
输入标题和内容
    ↓
系统自动解析双向链接
    ↓
添加标签（可选）
    ↓
保存笔记
    ↓
更新知识图谱
```

**知识检索流程：**
```
用户输入搜索内容
    ↓
判断搜索类型
    ├─ 关键词搜索 → 全文搜索 → 返回笔记列表
    └─ 自然语言问题 → RAG 检索 → AI 生成答案
```

---

## 4. 功能需求

### 4.1 用户认证模块

**FR-AUTH-001：用户登录**
- 系统支持简单的用户名密码登录
- 登录成功后生成 JWT Token
- Token 有效期为 7 天
- 支持记住登录状态

**FR-AUTH-002：用户登出**
- 用户可以主动登出
- 登出后清除 Token

**FR-AUTH-003：用户信息获取**
- 可以获取当前登录用户的基本信息

### 4.2 笔记管理模块

**FR-NOTE-001：创建笔记**
- 用户可以创建新笔记
- 必须输入笔记标题
- 内容支持 Markdown 格式
- 可以选择存放的文件夹
- 可以添加多个标签
- 创建时自动记录创建时间

**FR-NOTE-002：编辑笔记**
- 用户可以编辑已有笔记
- 支持修改标题、内容、文件夹、标签
- 编辑时自动更新修改时间
- 编辑时自动重新解析双向链接

**FR-NOTE-003：删除笔记**
- 用户可以删除笔记
- 删除前需要确认
- 删除后相关的链接关系自动清除

**FR-NOTE-004：查看笔记**
- 用户可以查看笔记详情
- 支持 Markdown 渲染预览
- 显示笔记的创建和修改时间
- 显示笔记的标签和文件夹

**FR-NOTE-005：笔记列表**
- 支持按文件夹过滤
- 支持按标签过滤
- 支持按时间排序
- 支持分页显示

### 4.3 Markdown 编辑器模块

**FR-EDIT-001：分屏编辑**
- 左侧为 Markdown 编辑区
- 右侧为实时预览区
- 支持同步滚动

**FR-EDIT-002：Markdown 语法支持**
- 支持标准 Markdown 语法
- 支持代码块语法高亮
- 支持表格、列表、引用等
- 支持双向链接语法 `[[笔记标题]]`

**FR-EDIT-003：编辑器工具栏**
- 提供常用格式化按钮
- 支持快捷键操作
- 支持全屏编辑模式

### 4.4 文件夹管理模块

**FR-FOLDER-001：文件夹结构**
- 支持最多 4 层文件夹嵌套结构
- Level 0：顶层文件夹
- Level 1：第1级子文件夹
- Level 2：第2级子文件夹
- Level 3：第3级子文件夹（最深）
- 笔记可以放在根目录或任意文件夹
- 每个分类（个人/工作/素材）有独立的文件夹树

**FR-FOLDER-002：文件夹操作**
- 创建文件夹（需指定父文件夹或为顶层）
- 创建时指定所属分类
- 重命名文件夹
- 删除文件夹（需先清空或移动内容）
- 移动内容到其他文件夹

**FR-FOLDER-003：文件夹显示**
- 侧边栏显示当前分类的文件夹树
- 支持展开/折叠
- 显示每个文件夹的内容数量

### 4.5 标签系统模块

**FR-TAG-001：标签管理**
- 创建标签（名称唯一）
- 为标签设置颜色
- 删除标签（不影响笔记）

**FR-TAG-002：笔记标签**
- 为笔记添加多个标签
- 从笔记移除标签
- 按标签过滤笔记

**FR-TAG-003：标签显示**
- 侧边栏显示所有标签
- 显示每个标签的笔记数量
- 标签使用自定义颜色显示

### 4.6 双向链接模块

**FR-LINK-001：链接创建**
- 支持 `[[笔记标题]]` 语法创建链接
- 编辑时自动解析链接语法
- 提取目标笔记 ID 并存储

**FR-LINK-002：链接显示**
- 预览时渲染为可点击链接
- 点击链接跳转到目标笔记
- 如果目标笔记不存在，显示为灰色

**FR-LINK-003：反向链接**
- 显示所有链接到当前笔记的其他笔记
- 实时查询生成，不存储
- 点击反向链接可跳转

### 4.7 知识图谱模块

**FR-GRAPH-001：全局图谱**
- 独立页面显示所有笔记的关系网络
- 节点类型区分（note/folder/tag）
- 不同类型节点使用不同颜色和大小
- 支持拖拽、缩放、点击

**FR-GRAPH-002：局部图谱**
- 编辑笔记时可展开的右侧面板
- 显示当前笔记的直接关联
- 包括链接的笔记和反向链接的笔记
- 点击节点可跳转

**FR-GRAPH-003：图谱交互**
- 支持鼠标拖拽移动视图
- 支持滚轮缩放
- 支持点击节点查看详情
- 支持悬停显示节点信息

### 4.8 搜索模块

**FR-SEARCH-001：全文搜索**
- 支持搜索笔记标题和内容
- 基于 SQLite FTS5 实现
- 支持按文件夹、标签过滤
- 返回匹配的笔记列表

**FR-SEARCH-002：AI 问答**
- 支持自然语言提问
- 基于 RAG 技术检索相关笔记
- 调用 LLM API 生成答案
- 支持多轮对话，保留最近 6 条历史消息作为上下文
- 对话历史保存到浏览器本地存储（localStorage）
- 支持创建、切换、删除多个独立对话
- 返回答案和相关笔记引用

### 4.9 AI 集成模块

**FR-AI-001：向量化**
- 使用阿里云通义千问 text-embedding-v3 API
- 云端服务，无需下载模型
- 笔记创建/更新时自动生成向量
- 存储到 FAISS 向量索引
- 向量维度：1024（支持长文本 up to 8192 tokens）

**FR-AI-002：RAG 检索**
- 用户问题向量化
- FAISS 检索 Top-K 相关笔记
- 构建提示词（问题 + 相关笔记）
- 调用 LLM API 生成答案

**FR-AI-003：API 配置**
- 支持配置第三方 LLM API
- 支持配置 API Key
- 支持选择模型（GPT-4、Claude 等）

**FR-AI-004：向量语义搜索** ✅ 已实现
- 支持单条向量搜索：GET /api/search/vector?q=xxx
- 支持批量向量搜索：POST /api/search/vector/batch
- 支持查询向量服务状态：GET /api/search/vector/status
- 支持重建向量索引：POST /api/search/vector/rebuild
- 优雅降级：模型不可用时自动回退到关键词搜索

### 4.10 内容分类体系（V2）

**FR-CATEGORY-001：分类管理**
- 系统预设三大分类：个人、工作、素材
- 用户可自定义新增分类
- 分类支持排序和图标设置
- 分类可删除（需先清空内容）

**FR-CATEGORY-002：内容类型管理**
- 每个分类下可创建多种内容类型
- 用户可自定义内容类型（如日记、简历、业务知识等）
- 内容类型支持自定义字段模板
- 内容类型可设置图标和颜色

**FR-CATEGORY-003：预设内容类型**
- 个人分类：笔记、日记、简历
- 工作分类：业务知识、管理知识
- 素材分类：图片、链接、视频

**FR-CATEGORY-004：素材存储**
- 小文件（< 10MB）：上传存储到系统
- 大文件（≥ 10MB）：仅存储外部链接
- 图片支持缩略图预览
- 视频支持封面图设置

### 4.11 Skill 智能模块（V3）

**FR-SKILL-001：Skill 定义**
- Skill 是可执行的智能模块
- 每个 Skill 包含：名称、描述、输入参数、执行逻辑、输出格式
- Skill 与知识库双向关联

**FR-SKILL-002：Skill 创建**
- 用户可手动创建 Skill
- 系统提供预设 Skill 模板库
- AI 可根据内容自动生成 Skill

**FR-SKILL-003：Skill 执行**
- 支持手动触发执行
- 支持定时自动执行（如每日固定时间）
- 执行结果可存回知识库
- 支持执行历史查看

**FR-SKILL-004：预设 Skill 模板**
- 对话总结 Skill：总结对话内容并归档
- 每日资讯 Skill：定时汇总资讯并归档
- 简历管理 Skill：简历解析、面试题生成
- 知识卡片 Skill：自动生成知识点卡片

**FR-SKILL-005：Skill 与知识库关联**
- Skill 可读取知识库内容作为输入
- Skill 执行结果自动存入指定分类
- 支持设置输出内容的标签和链接

### 4.12 提示词工程模块 (V3.1) ✅ 新增

**FR-PROMPT-001：提示词管理**
- 支持提示词的 CRUD 操作
- 提示词分为系统预设和用户自定义两类
- 系统预设提示词不可修改/删除
- 用户可创建自定义提示词覆盖系统预设

**FR-PROMPT-002：提示词数据结构**
- 名称、描述、分类（ai_chat/ai_search/skill/custom）
- 系统提示词（支持变量替换 `{variable_name}`）
- 用户提示词模板（可选）
- 输出格式说明
- 启用/禁用状态

**FR-PROMPT-003：敏感词过滤**
- 自动检测输入内容中的敏感词
- 支持的敏感词类别：暴力、色情、赌博、毒品、犯罪、欺诈
- 检测到敏感词时拒绝处理并提示用户

**FR-PROMPT-004：免责声明**
- AI 回复自动追加免责声明
- 免责声明内容：「以上内容仅供参考，不构成任何专业意见。如有医疗、法律、金融等领域的具体问题，请咨询相关专业人士。」

**FR-PROMPT-005：预设提示词模板**
- 知识问答（ai_chat）：基于知识库的智能问答助手
- AI搜索问答（ai_search）：用于全局搜索的 AI 问答提示词
- 对话总结（skill）：总结对话内容并归档
- 每日资讯（skill）：定时汇总资讯并归档
- 简历解析（skill）：解析简历内容，提取关键信息
- 知识卡片（skill）：自动生成知识点卡片

---

## 5. 非功能需求

### 5.1 性能要求

| 指标 | 要求 |
|------|------|
| 页面加载时间 | 首屏加载 < 3 秒 |
| 笔记保存响应 | < 500ms |
| 搜索响应时间 | < 1 秒 |
| 图谱渲染时间 | < 2 秒（100 个节点以内） |
| AI 问答响应 | < 10 秒 |

### 5.2 安全要求

**SEC-001：用户认证**
- 密码使用 bcrypt 加密存储
- JWT Token 用于 API 认证
- Token 有效期 7 天

**SEC-002：数据安全**
- 数据库文件存储在本地
- 敏感配置通过环境变量管理
- API Key 不记录在日志中
- **前后端分离架构**：API Key 存储在后端，通过环境变量加载，前端不接触任何 API Key

**SEC-003：输入验证**
- 所有用户输入进行验证和清理
- 防止 SQL 注入和 XSS 攻击

**SEC-004：API Key 安全配置**
- API Key 存储在后端 `.env` 文件中
- `.env` 文件已加入 `.gitignore`，不会提交到 Git 仓库
- 前端通过调用后端 API 使用 AI 功能，不直接调用第三方服务
- 生产环境建议使用系统环境变量替代 `.env` 文件

### 5.3 可用性要求

**USE-001：界面设计**
- 现代化卡片式布局
- 支持深色/浅色主题切换
- 响应式设计，支持不同屏幕尺寸

**USE-002：交互体验**
- 操作反馈及时
- 错误提示清晰
- 支持键盘快捷键

**USE-003：可访问性**
- 界面元素语义化
- 支持屏幕阅读器
- 颜色对比度符合 WCAG 标准

### 5.4 兼容性要求

**COMP-001：浏览器支持**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**COMP-002：运行环境**
- Python 3.11+
- Node.js 18+
- 支持 Windows、macOS、Linux

---

## 6. 数据模型

### 6.1 实体关系图

```
┌─────────────┐       ┌─────────────┐
│   users     │       │   folders   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ username    │       │ name        │
│ password    │       │ parent_id   │──┐
│ created_at  │       │ level       │  │
└─────────────┘       │ created_at  │◄─┘
                      └─────────────┘
                            │
                            │ 1:N
                            ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    tags     │       │    notes    │       │  note_tags  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ id (PK)     │──────►│ note_id(FK) │
│ name        │  N:M  │ title       │  N:M  │ tag_id (FK) │
│ color       │       │ content     │       └─────────────┘
│ created_at  │       │ folder_id   │
└─────────────┘       │ linked_ids  │
                      │ created_at  │
                      │ updated_at  │
                      └─────────────┘
```

### 6.2 数据表定义

**users 表：**
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**folders 表：**
```sql
CREATE TABLE folders (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    parent_id VARCHAR(36),
    level INTEGER CHECK (level IN (0, 1, 2, 3)),  -- 扩展至4层
    category_id VARCHAR(36),                        -- 所属分类（个人/工作/素材）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES folders(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**notes 表：**
```sql
CREATE TABLE notes (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    folder_id VARCHAR(36),
    linked_note_ids TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);
```

**tags 表：**
```sql
CREATE TABLE tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#00d4ff',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**note_tags 表：**
```sql
CREATE TABLE note_tags (
    note_id VARCHAR(36),
    tag_id VARCHAR(36),
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

### 6.3 扩展数据模型（V2/V3）

**categories 表（内容分类）：**
```sql
CREATE TABLE categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    color VARCHAR(7) DEFAULT '#00d4ff',
    sort_order INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**content_types 表（内容类型）：**
```sql
CREATE TABLE content_types (
    id VARCHAR(36) PRIMARY KEY,
    category_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    color VARCHAR(7) DEFAULT '#00d4ff',
    field_schema TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**contents 表（统一内容表）：**
```sql
CREATE TABLE contents (
    id VARCHAR(36) PRIMARY KEY,
    type_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    extra_fields TEXT,
    linked_content_ids TEXT,
    file_path VARCHAR(500),
    file_url VARCHAR(1000),
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (type_id) REFERENCES content_types(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**content_tags 表：**
```sql
CREATE TABLE content_tags (
    content_id VARCHAR(36),
    tag_id VARCHAR(36),
    PRIMARY KEY (content_id, tag_id),
    FOREIGN KEY (content_id) REFERENCES contents(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

**skills 表（Skill 智能模块）：**
```sql
CREATE TABLE skills (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    input_schema TEXT,
    output_schema TEXT,
    execution_logic TEXT,
    trigger_type VARCHAR(20) CHECK (trigger_type IN ('manual', 'scheduled', 'auto')),
    schedule_config TEXT,
    output_category_id VARCHAR(36),
    output_type_id VARCHAR(36),
    is_template BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (output_category_id) REFERENCES categories(id),
    FOREIGN KEY (output_type_id) REFERENCES content_types(id)
);
```

**skill_executions 表（Skill 执行记录）：**
```sql
CREATE TABLE skill_executions (
    id VARCHAR(36) PRIMARY KEY,
    skill_id VARCHAR(36) NOT NULL,
    input_data TEXT,
    output_data TEXT,
    output_content_id VARCHAR(36),
    status VARCHAR(20) CHECK (status IN ('running', 'success', 'failed')),
    error_message TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (output_content_id) REFERENCES contents(id)
);
```

**prompts 表（提示词模板）：** ✅ 新增
```sql
CREATE TABLE prompts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),                          -- 用户ID，NULL表示系统预设
    name VARCHAR(100) NOT NULL,                    -- 提示词名称
    description TEXT,                              -- 描述
    category VARCHAR(50) NOT NULL,                 -- 分类：ai_chat/ai_search/skill/custom
    system_prompt TEXT NOT NULL,                  -- 系统提示词（支持变量替换）
    user_prompt_template TEXT,                     -- 用户提示词模板
    output_format TEXT,                            -- 输出格式说明
    variables TEXT DEFAULT '[]',                   -- 变量列表 JSON
    is_system BOOLEAN DEFAULT FALSE,               -- 是否系统预设
    is_active BOOLEAN DEFAULT TRUE,                -- 是否启用
    is_default BOOLEAN DEFAULT FALSE,              -- 是否默认
    priority VARCHAR(20) DEFAULT 'normal',         -- 优先级
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 6.4 扩展实体关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  categories │       │content_types│       │   skills    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ id (PK)     │       │ id (PK)     │
│ name        │  1:N  │ category_id │──────►│ name        │
│ icon        │       │ name        │       │ description │
│ color       │       │ field_schema│       │ trigger_type│
│ is_system   │       │ is_system   │       │ schedule_   │
└─────────────┘       └─────────────┘       │ output_cat  │
      │                     │               │ output_type │
      │ 1:N                 │ 1:N           └─────────────┘
      ▼                     ▼                     │
┌─────────────┐       ┌─────────────┐             │
│  contents   │       │content_tags │             │
├─────────────┤       ├─────────────┤             │
│ id (PK)     │──────►│ content_id  │             │
│ type_id     │  N:M  │ tag_id      │             │
│ category_id │       └─────────────┘             │
│ title       │                                   │
│ content     │◄──────────────────────────────────┘
│ extra_fields│         (Skill 输出关联)
│ file_path   │
│ file_url    │
└─────────────┘
```

---

## 7. API 设计

### 7.1 API 端点列表

**认证 API：**
```
POST   /api/auth/login          # 登录
POST   /api/auth/logout         # 登出
GET    /api/auth/me             # 获取当前用户信息
```

**笔记 API：**
```
GET    /api/notes               # 获取笔记列表
POST   /api/notes               # 创建笔记
GET    /api/notes/:id           # 获取笔记详情
PUT    /api/notes/:id           # 更新笔记
DELETE /api/notes/:id           # 删除笔记
GET    /api/notes/:id/backlinks # 获取反向链接
```

**文件夹 API：**
```
GET    /api/folders             # 获取文件夹树
POST   /api/folders             # 创建文件夹
PUT    /api/folders/:id         # 更新文件夹
DELETE /api/folders/:id         # 删除文件夹
```

**标签 API：**
```
GET    /api/tags                # 获取所有标签
POST   /api/tags                # 创建标签
PUT    /api/tags/:id            # 更新标签
DELETE /api/tags/:id            # 删除标签
```

**搜索 API：**
```
GET    /api/search              # 全文搜索
POST   /api/search/ai           # AI 问答
```

**知识图谱 API：**
```
GET    /api/graph/global        # 全局图谱数据
GET    /api/graph/local/:id     # 局部图谱数据
```

**提示词 API：** ✅ 新增
```
GET    /api/prompts             # 获取提示词列表
POST   /api/prompts             # 创建提示词
GET    /api/prompts/:id         # 获取提示词详情
PUT    /api/prompts/:id         # 更新提示词
DELETE /api/prompts/:id         # 删除提示词
GET    /api/prompts/templates   # 获取提示词模板
POST   /api/prompts/initialize  # 初始化默认提示词
```

### 7.2 API 响应格式

**成功响应：**
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**错误响应：**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

---

## 8. 技术架构

### 8.1 技术栈

**前端：**
- Vue 3.4+ + TypeScript 5.x
- Pinia（状态管理）
- Vue Router 4.x（路由）
- Naive UI（组件库）
- markdown-it（Markdown 解析）
- Shiki（代码高亮）
- vue-force-graph（知识图谱）
- Tailwind CSS + SCSS（样式）
- Axios（HTTP 客户端）

**后端：**
- Python 3.11+
- FastAPI 0.109+（Web 框架）
- SQLAlchemy 2.x（ORM）
- SQLite 3.x（数据库）
- FAISS（向量索引）
- 通义千问 text-embedding-v3（文本向量化）
- LangChain（RAG 流程）
- python-jose（JWT 认证）

### 8.2 项目结构

```
知枢星图/
├── frontend/                 # Vue 3 前端项目
│   ├── src/
│   │   ├── assets/          # 静态资源
│   │   ├── components/      # 组件
│   │   ├── views/           # 页面视图
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── router/          # 路由配置
│   │   ├── api/             # API 客户端
│   │   ├── utils/           # 工具函数
│   │   ├── types/           # TypeScript 类型定义
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                 # Python 后端项目
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   ├── db/             # 数据库相关
│   │   └── utils/          # 工具函数
│   ├── main.py             # 应用入口
│   ├── requirements.txt
│   └── .env                # 环境变量配置
│
└── docs/                   # 文档
    └── superpowers/
        └── specs/
            └── 2026-03-17-zhishuxingtu-design.md
```

---

## 9. 界面设计

### 9.1 主界面布局（首页）

```
┌────────────────────────────────────────────────────────────┐
│  顶部导航栏                                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔍 搜索框                          ⚙️ 设置  👤 用户   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────┐
│                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│   │             │    │             │    │             │   │
│   │    个人     │    │    工作     │    │    素材     │   │
│   │   Personal  │    │    Work     │    │   Assets    │   │
│   │             │    │             │    │             │   │
│   └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 9.2 「个人」入口布局

```
┌────────────────────────────────────────────────────────────┐
│  顶部导航栏                                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔍 搜索框                          ⚙️ 设置  👤 用户   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
┌──────────────┬─────────────────────────────────────────────┐
│              │                                             │
│  [分类切换]  │                                             │
│  个人│工作│素材│                                            │
│              │                                             │
│  📁 笔记文件夹│         主内容区                            │
│  ▼ 编程学习   │                                             │
│    ▼ 前端    │                                             │
│      ▼ Vue  │                                             │
│        笔记1│                                             │
│        笔记2│                                             │
│  📝 智能检索 │                                             │
│  🔗 知识图谱 │                                             │
│  🤖 AI 助手  │                                             │
│              │                                             │
└──────────────┴─────────────────────────────────────────────┘
```

### 9.3 配色方案

**深色主题（默认）：**
- 主色调：深空灰 (#1a1a2e) + 霓虹蓝 (#00d4ff)
- 强调色：紫色 (#7b2cbf) + 青绿色 (#00ff9d)
- 背景：#0f0f1a（主背景）、#1a1a2e（卡片背景）
- 文字：#e5e5e5（主文字）、#a0a0a0（次要文字）

**浅色主题：**
- 主色调：浅灰白 (#f8f9fa) + 深蓝 (#2563eb)
- 强调色：紫色 (#8b5cf6) + 青绿色 (#10b981)
- 背景：#ffffff（主背景）、#f3f4f6（卡片背景）
- 文字：#1f2937（主文字）、#6b7280（次要文字）

**图谱节点颜色：**
- note：#00d4ff（深色主题）/ #2563eb（浅色主题）
- folder：#6b7280（灰色，节点稍大）
- tag：根据标签自定义颜色，节点稍小

---

## 10. 验收标准

### 10.1 功能验收

**用户认证：**
- [ ] 用户可以使用用户名密码登录
- [ ] 登录后可以获取用户信息
- [ ] 用户可以登出

**笔记管理：**
- [ ] 用户可以创建笔记
- [ ] 用户可以编辑笔记
- [ ] 用户可以删除笔记
- [ ] 用户可以查看笔记列表
- [ ] 用户可以查看笔记详情

**Markdown 编辑器：**
- [ ] 支持分屏编辑和预览
- [ ] 支持 Markdown 语法渲染
- [ ] 支持代码高亮
- [ ] 支持双向链接语法

**文件夹和标签：**
- [ ] 用户可以创建、编辑、删除文件夹
- [ ] 文件夹限制为 2 层
- [ ] 用户可以创建、编辑、删除标签
- [ ] 用户可以为笔记添加标签

**双向链接：**
- [ ] 支持 `[[笔记标题]]` 语法
- [ ] 链接可以正确跳转
- [ ] 反向链接正确显示

**知识图谱：**
- [ ] 全局图谱正确显示所有笔记关系
- [ ] 局部图谱正确显示当前笔记关联
- [ ] 图谱支持交互（拖拽、缩放、点击）
- [ ] 节点类型正确区分（颜色、大小）

**搜索：**
- [ ] 全文搜索返回正确结果
- [ ] AI 问答返回合理答案
- [ ] AI 问答引用相关笔记

### 10.2 性能验收

- [ ] 首屏加载时间 < 3 秒
- [ ] 笔记保存响应 < 500ms
- [ ] 搜索响应时间 < 1 秒
- [ ] 图谱渲染时间 < 2 秒（100 节点内）

### 10.3 安全验收

- [ ] 密码正确加密存储
- [ ] JWT Token 认证正常工作
- [ ] API Key 不暴露在日志中
- [ ] 输入验证防止注入攻击

---

## 11. 风险评估

### 11.1 潜在风险

| 风险 | 影响 | 可能性 | 描述 |
|------|------|--------|------|
| AI API 调用失败 | 高 | 中 | 第三方 LLM API 可能不稳定或超时 |
| 向量索引性能 | 中 | 低 | 大量笔记时 FAISS 索引可能变慢 |
| 浏览器兼容性 | 中 | 低 | 某些浏览器可能不支持部分功能 |
| 数据丢失 | 高 | 低 | 本地数据库可能因意外损坏 |

### 11.2 缓解策略

**AI API 调用失败：**
- 实现重试机制
- 提供友好的错误提示
- 支持配置多个 API 提供商

**向量索引性能：**
- 定期优化索引
- 限制单次检索数量
- 监控索引大小

**浏览器兼容性：**
- 明确支持的浏览器版本
- 提供降级方案
- 充分测试主流浏览器

**数据丢失：**
- 实现自动备份功能
- 提供手动导出功能
- 记录操作日志

---

## 12. 项目计划

### 12.1 开发阶段

**第一阶段（Day 1 上午）：项目初始化**
- 搭建前端 Vue 3 项目
- 搭建后端 FastAPI 项目
- 配置数据库和基础模型
- 实现用户认证

**第二阶段（Day 1 下午）：核心功能**
- 笔记 CRUD
- 文件夹管理（2 层限制）
- 标签系统
- Markdown 编辑器（分屏预览）

**第三阶段（Day 2 上午）：进阶功能**
- 双向链接系统
- 反向链接查询
- 全文搜索（SQLite FTS5）
- 知识图谱可视化（全局 + 局部）

**第四阶段（Day 2 下午）：AI 集成和收尾**
- RAG 问答系统（单轮）
- FAISS 向量索引
- 界面优化（双主题）
- 测试和调试

### 12.2 里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| 项目初始化完成 | Day 1 中午 | 前后端项目骨架、用户认证 |
| 核心功能完成 | Day 1 晚上 | 笔记管理、编辑器、文件夹标签 |
| 进阶功能完成 | Day 2 中午 | 双向链接、搜索、知识图谱 |
| MVP 发布 | Day 2 晚上 | 完整可用的 MVP 版本 |

### 12.3 迭代规划

**V1 - MVP（当前阶段）**
- 目标：完成核心笔记管理功能
- 周期：2 天
- 交付：可用的个人知识库基础版本

**V2 - 内容分类升级**
- 目标：实现内容分类体系和素材管理
- 周期：3-5 天
- 主要功能：
  - 三大预设分类（个人/工作/素材）
  - 自定义分类和内容类型
  - 素材混合存储
  - 内容类型模板
- 交付：支持多类型内容的知识管理平台

**V3 - Skill 智能模块**
- 目标：实现 Skill 系统和自动化能力
- 周期：5-7 天
- 主要功能：
  - Skill 创建和管理
  - Skill 执行引擎
  - 预设 Skill 模板
  - AI 自动生成 Skill
- 交付：具备智能自动化能力的知识平台

**V4 - 扩展功能**
- 目标：完善生态和高级功能
- 周期：持续迭代
- 主要功能：
  - 语义搜索
  - 数据导入导出
  - 浏览器插件
  - 批量导入
- 交付：功能完善的个人知识资产管理平台

### 12.4 版本演进路线图

```
V1 MVP          V2 分类升级       V3 Skill         V4 扩展
  │                │                │                │
  ▼                ▼                ▼                ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 笔记管理 │    │ 分类体系 │    │ Skill   │    │ 语义搜索 │
│ 文件夹   │ -> │ 内容类型 │ -> │ 执行引擎 │ -> │ 导入导出 │
│ 标签     │    │ 素材管理 │    │ AI生成  │    │ 浏览器插件│
│ 双向链接 │    │ 模板系统 │    │ 自动化  │    │ 批量处理 │
│ 知识图谱 │    │          │    │         │    │         │
│ AI问答   │    │          │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
   Day 2          +3-5天         +5-7天          持续
```

---

## 13. 附录

### 13.1 术语表

| 术语 | 定义 |
|------|------|
| MVP | Minimum Viable Product，最小可行产品 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| JWT | JSON Web Token，用于身份认证的令牌 |
| FTS | Full-Text Search，全文搜索 |
| ORM | Object-Relational Mapping，对象关系映射 |
| Skill | 可执行的智能模块，类似 AI Agent 技能包 |
| 内容分类 | 知识内容的顶层分类（个人/工作/素材等） |
| 内容类型 | 分类下的具体内容类型（笔记/日记/简历等） |
| 提示词工程 | Prompt Engineering，优化 AI 模型输入以获得更好输出的实践 |

### 13.2 参考资源

- [Vue 3 官方文档](https://vuejs.org/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangChain 文档](https://python.langchain.com/)
- [FAISS 文档](https://faiss.ai/)
- [markdown-it 文档](https://github.com/markdown-it/markdown-it)

---

## 文档历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0.0 | 2026-03-17 | 产品团队 | 初始版本，MVP 需求定义 |
| v1.1.0 | 2026-03-18 | 产品团队 | 增加升级版愿景：内容分类体系 + Skill 智能模块 |
| v1.4.1 | 2026-03-19 | 产品团队 | 更新 AI 问答功能：支持多轮对话和历史记录保存 |
| v1.5.0 | 2026-03-19 | 产品团队 | 向量语义搜索功能完成，V4 部分功能实现 |
| v1.5.1 | 2026-03-19 | 产品团队 | API Key 安全配置说明添加 |
| v1.5.2 | 2026-03-19 | 产品团队 | 向量模型从 MiniLM 升级为通义千问 text-embedding-v3 |
| v1.5.3 | 2026-03-19 | 产品团队 | 提示词工程完善：提示词管理、敏感词过滤、免责声明、6个预设模板 |
| v1.6.0 | 2026-03-19 | 产品团队 | LangChain 框架集成完成：支持渐进式迁移，所有功能开关已开启 |
| v1.7.0 | 2026-03-20 | 产品团队 | 向量长期记忆：基于 FAISS 的对话记忆向量存储，支持语义检索历史对话 |
| v1.8.0 | 2026-03-20 | 产品团队 | 提示词工程进阶：Few-Shot示例库、A/B测试框架、CoT思维链、效果评估系统 |
| v1.9.0 | 2026-03-21 | 产品团队 | Reranker重排序：Cross-Encoder精排、对比测试API、优雅降级、检索精度提升20-30% |
| v2.0.0 | 2026-03-21 | 产品团队 | SSE流式输出：Server-Sent Events实现、逐字实时显示、打字机效果、停止生成功能、验收标准和用户故事 |
| v1.9.0 | 2026-03-20 | 产品团队 | 提示词链编排引擎：多步骤任务编排、3个预设链模板、链式调用执行 |
