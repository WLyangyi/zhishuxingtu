# 知枢星图 - 个人知识库系统

> 🚀 现代化的个人知识资产管理平台，支持双向链接、知识图谱、AI 智能问答

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vue 3.4+](https://img.shields.io/badge/Vue-3.4%2B-brightgreen)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-blue)](https://fastapi.tiangolo.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green)](https://www.python.org/)

## ✨ 特性亮点

### 🎯 核心功能
- **📝 笔记管理** - Markdown 编辑器，分屏预览，语法高亮
- **🔗 双向链接** - `[[笔记标题]]` 语法，建立知识关联
- **🕸️ 知识图谱** - 全局/局部图谱可视化，直观探索知识网络
- **🔍 智能检索** - 全文搜索 + AI 智能问答

### 🤖 AI 智能
- **RAG 检索增强生成** - 基于知识库的 AI 问答
- **SSE 流式输出** - 逐字实时显示，打字机效果
- **语义分块** - 按语义边界分割，提升检索精度
- **混合检索** - 向量 + BM25 融合，召回率提升 15-25%
- **Reranker 重排序** - Cross-Encoder 精排，检索精度提升 20-30%
- **向量长期记忆** - 基于 FAISS 的对话记忆，突破轮数限制

### 🎨 内容组织
- **三大入口** - 个人 / 工作 / 素材分类
- **4 层嵌套文件夹** - 灵活的知识结构
- **标签系统** - 自定义颜色，扁平化标签管理
- **Skill 智能模块** - 可执行的 AI 技能包

### 🛡️ 安全可靠
- **前后端分离** - API Key 存储在后端，不暴露在前端
- **JWT 认证** - 安全的身份验证机制
- **环境变量配置** - 敏感信息通过环境变量管理

## 🏗️ 技术栈

### 前端
| 技术 | 说明 |
|------|------|
| Vue 3.4+ | 渐进式 JavaScript 框架 |
| TypeScript 5.x | 类型安全的 JavaScript |
| Pinia | Vue 状态管理 |
| Naive UI | Vue 3 组件库 |
| Tailwind CSS | 原子化 CSS |
| Shiki | 代码高亮 |

### 后端
| 技术 | 说明 |
|------|------|
| Python 3.11+ | 高性能后端语言 |
| FastAPI 0.109+ | 现代 Web 框架 |
| SQLAlchemy 2.x | ORM 框架 |
| FAISS | Facebook 开源向量索引 |
| LangChain | RAG 应用开发框架 |
| 通义千问 embedding | 阿里云文本向量化服务 |

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd 知枢星图
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

`.env.example` 配置项：
```env
# 阿里云 DashScope API（用于文本向量化）
DASHSCOPE_API_KEY=your_api_key_here

# JWT 密钥
JWT_SECRET_KEY=your_secret_key_here

# LLM 模型配置（可选，默认为通义千问）
LLM_API_KEY=your_api_key_here
LLM_MODEL=qwen-plus
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 5. 访问应用

打开浏览器访问 `http://localhost:5173`

## 📁 项目结构

```
知枢星图/
├── frontend/                 # Vue 3 前端项目
│   ├── src/
│   │   ├── api/             # API 客户端
│   │   ├── components/      # Vue 组件
│   │   ├── views/           # 页面视图
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── router/          # 路由配置
│   │   ├── types/           # TypeScript 类型
│   │   └── utils/           # 工具函数
│   └── package.json
│
├── backend/                  # Python 后端项目
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # Pydantic 模型
│   │   ├── services/        # 业务逻辑
│   │   └── main.py          # 应用入口
│   ├── requirements.txt
│   └── .env.example
│
└── docs/                    # 项目文档
```

## 🎨 界面预览

### 首页 - 三大入口
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    个人     │    │    工作     │    │    素材     │
│   Personal  │    │    Work     │    │   Assets    │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 「个人」知识空间
- 📁 笔记文件夹（支持 4 层嵌套）
- 🔍 智能检索
- 🔗 知识图谱
- 🤖 AI 助手

## 🔧 API 接口

### 认证
```
POST /api/auth/login     # 登录
POST /api/auth/logout    # 登出
GET  /api/auth/me        # 获取当前用户
```

### 笔记
```
GET    /api/notes              # 获取笔记列表
POST   /api/notes              # 创建笔记
GET    /api/notes/:id           # 获取笔记详情
PUT    /api/notes/:id           # 更新笔记
DELETE /api/notes/:id           # 删除笔记
GET    /api/notes/:id/backlinks # 获取反向链接
```

### 搜索
```
GET  /api/search              # 全文搜索
POST /api/search/ai           # AI 问答
GET  /api/search/vector       # 向量搜索
```

### 知识图谱
```
GET /api/graph/global         # 全局图谱
GET /api/graph/local/:id      # 局部图谱
```

## 📚 文档

- [产品需求文档 (PRD)](docs/superpowers/specs/prd.md)
- [开发实施文档](docs/开发实施文档.md)
- [技术架构文档](docs/技术架构.md)

## 🗺️ 版本演进

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
```

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<p align="center">
Made with ❤️ for personal knowledge management
</p>
