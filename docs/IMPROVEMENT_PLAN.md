# BUCT Media System 改进计划

> 本文档为项目渐进式改进路线图，按阶段逐步实施。每完成一项，在对应 `[ ]` 前加 `x` 标记。
>
> **最后更新**: 2026-03-09

---

## 阶段一：安全加固（P0）

> 目标：消除生产环境安全隐患，确保系统基本安全

### 1.1 JWT 安全增强
- [x] **SECRET_KEY 启动校验** — 在 `main.py` 启动时检查 `SECRET_KEY` 是否为默认值，若是则拒绝启动并提示配置
- [x] **Refresh Token 机制** — 引入 Refresh Token（HttpOnly Cookie），Access Token 短效（15min）+ Refresh Token 长效（7d），添加 `POST /auth/refresh` 端点
- [x] **废弃 API 修正** — 将 `datetime.utcnow()` 替换为 `datetime.now(datetime.UTC)`（Python 3.12+ 兼容）

### 1.2 注册保护
- [x] **接口限流** — 引入 `slowapi` 对 `/auth/register` 和 `/auth/login` 添加 Rate Limit（如 5次/分钟）
- [x] **注册审批模式（可选）** — 添加系统设置项，可选择"开放注册"或"管理员审批注册"

### 1.3 全局异常处理
- [x] **统一 Exception Handler** — 在 `main.py` 注册全局异常处理器，生产环境隐藏堆栈信息，返回标准化错误格式 `{ "detail": "...", "code": "..." }`
- [x] **请求日志中间件** — 添加请求日志中间件，记录请求路径、耗时、状态码

### 1.4 CORS 收紧
- [x] **生产环境 CORS** — 通过 `.env` 配置 `ALLOWED_ORIGINS`，默认开发环境保持当前值，生产环境必须显式指定域名；`allow_methods` 限制为 `GET, POST, PUT, DELETE, OPTIONS`

**涉及文件**:
- `backend/app/main.py` — 异常处理器、启动校验
- `backend/app/core/security.py` — Refresh Token 生成/校验
- `backend/app/core/config.py` — 新增配置项
- `backend/app/api/v1/endpoints/auth.py` — refresh 端点、限流
- `backend/requirements.txt` — 添加 `slowapi`

---

## 阶段二：功能补全（P1）

> 目标：补齐日常使用中的关键功能缺失

### 2.1 密码管理 + SSO 预留
- [x] **修改密码** — 添加 `PUT /auth/password` 端点，需提供旧密码验证
- [x] **管理员重置密码** — 添加 `PUT /admin/users/{id}/password` 端点，无需旧密码
- [x] **SSO/OAuth 预留** — User 模型添加 `auth_provider`/`sso_id` 字段，`config.py` 添加 SSO 配置项（待学校文档后实现实际对接）
- [x] **前端入口** — 在用户下拉菜单和管理后台中添加"修改密码"对话框

### 2.2 操作审计日志
- [x] **AuditLog 模型** — 新建 `models/audit_log.py`，字段：`id, user_id, action, resource_type, resource_id, detail, ip_address, created_at`
- [x] **审计 API** — 新建 `admin_audit.py`，`GET /admin/audit-logs` 支持按时间、用户、操作类型筛选
- [x] **审计装饰器/中间件** — 在关键操作（审核通过/拒绝、删除、批量操作）6处埋入审计日志
- [x] **管理后台日志页面** — 新增 `admin/AuditLog.vue`，支持按操作类型、资源类型、用户筛选

### 2.3 站内通知
- [x] **Notification 模型** — 新建 `models/notification.py`，字段：`id, user_id, type, title, content, is_read, related_id, created_at`
- [x] **通知触发** — 照片审核通过/拒绝时自动创建通知（`services/notification.py`）
- [x] **通知 API** — `GET /user/notifications`、`GET /user/notifications/unread-count`、`PUT /user/notifications/{id}/read`、`PUT /user/notifications/read-all`
- [x] **前端通知中心** — `NotificationBell.vue` 铃铛组件（Badge+Popover），60秒轮询，已集成到 Gallery 和 AdminLayout

### 2.4 用户个人中心
- [x] **Profile API** — `GET /user/profile` 和 `PUT /user/profile`（修改邮箱/姓名）
- [x] **资料编辑** — 支持修改昵称、邮箱，密码走 `PUT /auth/password`

### 2.5 照片互动
- [x] **收藏功能** — 新建 `Favorite` 模型 + `POST /photos/{id}/favorite`（toggle） + `GET /photos/{id}/favorite` + `GET /photos/favorites/my`
- [ ] **评论功能（可选/后续）** — 新建 `Comment` 模型 + 评论 API + 照片详情页评论区

**涉及文件（新增）**:
- `backend/app/models/audit_log.py`
- `backend/app/models/notification.py`
- `backend/app/models/favorite.py`
- `backend/app/api/v1/endpoints/notifications.py`
- `backend/app/api/v1/endpoints/favorites.py`
- `frontend/src/views/Profile.vue`
- `frontend/src/views/admin/AuditLog.vue`
- `frontend/src/api/notifications.ts`
- `frontend/src/api/favorites.ts`
- Alembic 迁移文件

---

## 阶段三：性能优化（P3）

> 目标：优化关键路径性能，降低不必要的资源消耗

### 3.1 系统配置缓存
- [ ] **内存 TTL 缓存** — 为 `get_system_config` 添加 `cachetools.TTLCache`（TTL=60s），配置变更 API 中主动清除缓存
- [ ] **依赖** — 添加 `cachetools` 到 `requirements.txt`

### 3.2 图片响应缓存
- [ ] **Cache-Control 头** — 为图片/缩略图响应添加 `Cache-Control: public, max-age=86400`
- [ ] **ETag 支持** — 基于文件修改时间或 hash 生成 ETag，支持 `304 Not Modified`

### 3.3 分页安全限制
- [ ] **硬上限** — 在 `list_public_photos` 和 `list_photos` 中添加 `limit = min(limit, 100)` 保护
- [ ] **默认值调整** — 统一默认分页大小为 20，最大 100

### 3.4 数据库连接池
- [ ] **连接池参数** — 在 `database.py` 中为 PostgreSQL 配置 `pool_size=10, max_overflow=20, pool_pre_ping=True`
- [ ] **SQLite 优化** — 为开发 SQLite 添加 `check_same_thread=False` 和 WAL 模式

**涉及文件**:
- `backend/app/core/deps.py` — 配置缓存
- `backend/app/core/database.py` — 连接池配置
- `backend/app/api/v1/endpoints/photos.py` — 缓存头、分页限制
- `backend/app/services/storage.py` — ETag 生成
- `backend/requirements.txt` — 添加 `cachetools`

---

## 阶段四：用户体验增强（P4）

> 目标：提升前端交互品质，让系统更好用

### 4.1 前端错误处理优化
- [ ] **Axios 全局拦截器** — 在 `api/index.ts` 中统一处理：401 自动跳转登录、403 权限提示、网络超时、500 服务端错误
- [ ] **NaiveUI Message 提示** — 用 `useMessage()` 替代 `console.error`，给用户友好的错误提示

### 4.2 画廊无限滚动
- [ ] **Intersection Observer** — 替换手动翻页为滚动到底部自动加载下一页
- [ ] **加载状态** — 底部显示加载动画骨架屏，全部加载完成显示"没有更多了"

### 4.3 分享功能
- [ ] **复制链接** — 照片详情页添加"复制链接"按钮
- [ ] **二维码分享（可选）** — 生成照片访问二维码

### 4.4 上传体验优化
- [ ] **实时进度条** — 使用 Axios `onUploadProgress` 在上传界面显示每个文件的进度百分比
- [ ] **上传预览** — 选择文件后立即显示缩略图预览

### 4.5 搜索增强
- [ ] **搜索建议** — 输入时展示匹配的标签/分类建议（Typeahead）
- [ ] **拍摄时间筛选** — 添加日期范围选择器，按 `captured_at` 筛选
- [ ] **全文搜索（可选/后续）** — SQLite FTS5 或 PostgreSQL `pg_trgm` 全文检索

**涉及文件**:
- `frontend/src/api/index.ts` — 拦截器
- `frontend/src/views/Gallery.vue` — 无限滚动、搜索增强
- `frontend/src/views/Upload.vue` — 进度条
- `frontend/src/components/` — 新增分享组件

---

## 阶段五：移动端适配（P5）

> 目标：确保核心页面在手机和平板上体验良好

### 5.1 响应式布局审查与修复
- [ ] **画廊页** — 确保 MasonryLayout 在 `<768px` 屏幕上降为 1-2 列，触摸友好的交互
- [ ] **上传页** — 移动端触控区域适配，文件选择按钮放大
- [ ] **管理后台** — 侧边栏在移动端收缩为抽屉菜单
- [ ] **登录页** — 表单在移动端居中、宽度自适应

### 5.2 移动端交互优化
- [ ] **触摸手势** — 照片详情页支持左右滑动切换
- [ ] **下拉刷新** — 画廊页支持下拉刷新

### 5.3 PWA 基础支持（可选）
- [ ] **manifest.json** — 添加 Web App Manifest，支持"添加到主屏幕"
- [ ] **Service Worker** — 基本离线缓存（静态资源）

**涉及文件**:
- `frontend/src/components/common/MasonryLayout.vue` — 响应式列数
- `frontend/src/layouts/AdminLayout.vue` — 移动端抽屉菜单
- `frontend/src/views/*.vue` — 各页面媒体查询
- `frontend/public/manifest.json` — PWA 配置（新增）

---

## 实施原则

1. **每次只做一个小节**（如 1.1、1.2），完成后打勾，提交代码
2. **先改后端，再改前端** — 每个功能先确保 API 可用，再实现界面
3. **每个阶段完成后做一次集成测试** — 确保无回归
4. **阶段间无硬依赖** — P3/P4/P5 可与 P1 并行推进

---

## 进度总览

| 阶段               | 条目      | 完成      | 状态     |
| ------------------ | --------- | --------- | -------- |
| 阶段一：安全加固   | 8 项      | 8/8       | ✅ 已完成 |
| 阶段二：功能补全   | 14 项     | 13/14     | ✅ 已完成 |
| 阶段三：性能优化   | 7 项      | 0/7       | ⬜ 未开始 |
| 阶段四：UX 增强    | 10 项     | 0/10      | ⬜ 未开始 |
| 阶段五：移动端适配 | 8 项      | 0/8       | ⬜ 未开始 |
| **合计**           | **47 项** | **21/47** |          |
