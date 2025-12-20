# BUCT Media HUB - 智能照片管理系统

## 项目简介

BUCT Media HUB 是基于现有 BUCT Tagger 系统的 Web 化升级版本，旨在将原有的本地脚本工作流转化为一个现代化的智能图片管理平台。系统集成了 AI 自动打标、批量导入、照片审核及可视化统计等功能，为校园媒体资源提供全生命周期的管理。

### 核心功能

- 📸 **批量上传与导入** - 支持单张/批量上传，以及从旧版 BUCT Tagger 系统一键导入历史数据。
- 🤖 **AI 智能打标** - 集成 Ollama 本地大模型，自动识别季节、分类、关键物体及场景描述。
- ✅ **审核工作流** - 完善的照片审核机制，支持批量上线、下线及信息修正。
- 🔍 **多维搜索** - 支持按季节、类别、校区、标签及拍摄时间进行快速筛选。
- 📊 **数据统计** - 提供可视化仪表盘，直观展示照片分布、标签热度及系统状态。
- 🔐 **权限管理** - 基于 JWT 的认证系统，区分管理员与普通用户权限。

### 技术栈

**后端**
- **FastAPI**: 现代高性能异步 Web 框架。
- **SQLAlchemy 2.0**: 强大的异步 ORM 支持。
- **SQLite + aiosqlite**: 轻量级异步数据库（MVP 阶段）。
- **Pillow**: 图像处理与缩略图生成。
- **Ollama**: 本地 AI 视觉语言模型服务。
- **Alembic**: 数据库迁移管理。

**前端**
- **Vue 3 (Composition API)**: 渐进式 JavaScript 框架。
- **TypeScript**: 全程类型安全。
- **Vite**: 极速构建与开发体验。
- **Naive UI**: 现代化、可定制的 UI 组件库。
- **Tailwind CSS**: 实用优先的 CSS 框架。
- **Pinia**: 响应式状态管理。
- **ECharts**: 数据可视化图表。

**存储**
- 本地文件系统 (`./uploads`)：存储原图与缩略图。

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (可选，用于 AI 自动打标)

### 后端配置与启动

1. **安装依赖**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **数据库迁移**:
   ```bash
   alembic upgrade head
   ```

3. **创建管理员账号**:
   ```bash
   python scripts/create_admin.py
   ```

4. **启动服务**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 前端配置与启动

1. **安装依赖**:
   ```bash
   cd frontend
   npm install
   ```

2. **启动开发服务器**:
   ```bash
   npm run dev
   ```

### 访问地址

- **前端界面**: [http://localhost:5173](http://localhost:5173)
- **API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 默认管理员账号

- **账号**: `admin@buct.edu.cn`
- **密码**: `admin123` (请在首次登录后及时修改)

## 测试

### 后端测试
```bash
cd backend
pytest
```

## 项目结构

```text
BUCT_Media_System/
├── backend/              # 后端代码 (FastAPI)
│   ├── app/
│   │   ├── api/         # API 路由与端点
│   │   ├── core/        # 核心配置 (安全, 数据库, 依赖)
│   │   ├── crud/        # 数据库操作逻辑
│   │   ├── models/      # SQLAlchemy 模型
│   │   ├── schemas/     # Pydantic 数据模型
│   │   └── services/    # 业务逻辑 (AI, 导入, 存储)
│   ├── alembic/         # 数据库迁移脚本
│   ├── docs/            # 后端开发文档与报告
│   └── tests/           # 单元测试与集成测试
├── frontend/            # 前端代码 (Vue 3)
│   ├── src/
│   │   ├── api/         # 接口请求封装
│   │   ├── components/  # 可复用组件
│   │   ├── stores/      # Pinia 状态管理
│   │   ├── views/       # 页面视图
│   │   └── types/       # TypeScript 类型定义
├── scripts/             # 运维与初始化脚本
└── uploads/             # 媒体文件存储目录
```

## 开发进度

目前已完成 **阶段 1: 后端核心开发** (Sprint 1.1 - 1.7)，系统核心闭环已打通。

- [x] **Sprint 1.1**: 数据库模型与基础设施
- [x] **Sprint 1.2**: 认证系统 (JWT)
- [x] **Sprint 1.3**: 照片上传与处理 API
- [x] **Sprint 1.4**: 照片审核与批量管理
- [x] **Sprint 1.5**: 标签管理系统
- [x] **Sprint 1.6**: AI 自动打标集成 (Ollama)
- [x] **Sprint 1.7**: 历史数据批量导入

详细进度请参阅 [backend/docs/DEVELOPMENT_PROGRESS.md](backend/docs/DEVELOPMENT_PROGRESS.md)。

## 贡献指南

欢迎贡献代码！请遵循以下规范：

### Git Commit 规范

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例: `feat(auth): implement login functionality`

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。

---

**开发愉快！🚀**

