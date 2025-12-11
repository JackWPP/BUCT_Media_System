# BUCT Media System 项目评估与代码 Review 报告

## 1. 总体评估 (Executive Summary)

经过详细的代码审查，**BUCT Media HUB** 项目目前的完成度远高于 `README.md` 中展示的进度。它已经具备了一个完整的 MVP (最小可行性产品) 形态，核心功能包括图片上传、AI 自动打标、元数据管理和前端展示均已实现。

*   **完成度**: 约 80% (MVP 标准)
*   **代码质量**: 高。后端结构清晰，遵循 FastAPI 最佳实践；前端组件化良好。
*   **主要差异**: `README.md` 和 `mission.md` 中的架构规划（PostgreSQL + MinIO）与实际代码实现（SQLite + 本地文件系统）存在差异，且前端缺失文档中提到的 TailwindCSS。

---

## 2. 架构与设计 Review

### 2.1 规划 vs 实现

| 维度 | 规划设计 (Design Docs) | 实际代码 (Implementation) | 评价 |
| :--- | :--- | :--- | :--- |
| **数据库** | PostgreSQL + pgvector | **SQLite** (`aiosqlite`) | 对于本地单机 MVP 是合理的选择，降低了部署难度，但限制了未来向量搜索的扩展。 |
| **文件存储** | MinIO 对象存储 | **本地文件系统** (`./uploads`) | 简化了依赖，但失去了 S3 协议的通用性和分布式扩展能力。 |
| **AI 引擎** | Ollama (LLaVA/Moondream) | **Ollama** | 一致。实现了完整的异步调用和结果解析逻辑。 |
| **前端样式** | TailwindCSS | **Standard CSS** + Naive UI | **存在偏差**。`package.json` 中缺失 `tailwindcss`，大量样式手写在 Vue 组件中。 |
| **布局模式** | 瀑布流 (Masonry) | **标准网格** (`n-grid`) | 标准网格对不同长宽比的图片展示效果不如瀑布流，可能导致排版空隙。 |

---

## 3. 详细代码 Review

### 3.1 后端 (Backend)

**优点:**
*   **结构规范**: 采用了典型的 FastAPI 分层架构 (`api`, `core`, `crud`, `models`, `schemas`, `services`)，代码解耦做得很好。
*   **异步设计**: 全程使用 `async/await`，包括数据库操作和文件 I/O，保证了高性能。
*   **AI 集成**: `ai_tagging.py` 封装完善，包含了图片压缩（适配 VLM 输入）、Prompt 构建、JSON 容错解析等健壮性逻辑。
*   **后台任务**: 正确使用了 `BackgroundTasks` 处理耗时的 AI 分析任务，避免阻塞上传请求。

**改进点:**
1.  **数据库配置**: `config.py` 硬编码了 SQLite。建议保留 PostgreSQL 的配置选项（即使默认关闭），以便随时切换。
2.  **依赖注入**: `deps.py` 中虽然使用了 `yield`，但对于 SQLite 是否开启了 WAL 模式以处理高并发写入尚不明确。
3.  **错误处理**: `ai_tagging.py` 中虽然有 try-except，但若 Ollama 服务未启动，建议在应用启动时 (`main.py` startup event) 进行一次连接检查并发出警告。

### 3.2 前端 (Frontend)

**优点:**
*   **技术栈先进**: Vue 3 setups, TypeScript, Pinia, Vite。
*   **组件化**: 拆分了 `PhotoDetail`, `EmptyState` 等组件，逻辑清晰。
*   **状态管理**: Store (`photo.ts`, `auth.ts`) 职责分明。

**缺陷与风险:**
1.  **缺失 TailwindCSS**: 虽然 README 提到了 Tailwind，但 `package.json` 没有安装，`vite.config.ts` 也没有配置。现有的 CSS (`Gallery.vue`) 是手动编写的 scoped css。这会导致后续样式维护成本变高，且不符合设计文档。
2.  **布局问题**: `Gallery.vue` 使用了 `n-grid`。这在展示横竖构图混杂的照片时，会强制对齐行高或留下空白，无法达到设计文档中要求的“瀑布流”沉浸式体验。
3.  **类型安全**: 部分 API 调用处使用了类型断言或 `any`，可以进一步严格化。

---

## 4. 关键问题清单 (Critical Issues)

以下问题需要优先解决：

1.  **依赖缺失**: 前端项目缺失 `tailwindcss` 及其配置。
2.  **布局体验**: 图片展示页未实现真正的瀑布流布局。
3.  **文档不同步**: `README.md` 中的 "开发进度" 严重滞后，且架构描述误导（声称使用了 Postgres/MinIO）。

---

## 5. 改进建议 (Action Plan)

### 第一阶段：修复与对齐 (Immediate)
*   [ ] **更新文档**: 修改 `README.md` 以反映当前 SQLite + Local Storage 的 MVP 架构，并更新任务清单。
*   [ ] **安装 Tailwind**: 在前端安装并配置 TailwindCSS，逐步替换手写 CSS。
*   [ ] **AI 服务检查**: 在后端启动时增加对 Ollama 端口的健康检查。

### 第二阶段：体验优化 (Enhancement)
*   [ ] **实现瀑布流**: 引入 `vue-masonry-wall` 或类似库替换 `n-grid`，实现真正的照片墙效果。
*   [ ] **图片懒加载/缩略图**: 确认后端 `image_processing.py` 是否生成了多级缩略图，并确保前端在列表中仅加载缩略图以提升性能。

### 第三阶段：架构演进 (Future)
*   [ ] **数据库迁移**: 随着数据量增长，迁移至 PostgreSQL。
*   [ ] **存储迁移**: 引入 MinIO，解耦文件存储，为容器化和集群部署做准备。

总体而言，代码基础非常扎实，是一个高质量的起步项目。
