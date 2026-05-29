# 视觉北化 API 手册

> 最后更新：2026-05-28
> 基础路径：`https://tkjs.buct.edu.cn/api/v1`

---

## 📋 目录

- [认证](#认证)
- [照片管理](#照片管理)
- [标签管理](#标签管理)
- [搜索](#搜索)
- [分类系统](#分类系统)
- [统计](#统计)
- [用户管理](#用户管理)

---

## 🔐 认证

### 登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "identifier": "username_or_email",
  "password": "your_password"
}
```

**响应**：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "username",
    "role": "admin"
  }
}
```

### 注册

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123"
}
```

---

## 📷 照照管理

### 获取公开照片列表

```http
GET /api/v1/photos/public
```

**查询参数**：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `page` | int | 页码 | `1` |
| `page_size` | int | 每页数量 | `30` |
| `season` | string | 季节筛选 | `秋季` |
| `campus` | string | 校区筛选 | `昌平校区` |
| `building` | string | 楼宇筛选 | `图书馆` |
| `gallery_series` | string | 专题筛选 | `昌平校区摄影大赛` |
| `gallery_year` | string | 年份筛选 | `2025年第八届获奖作品` |
| `award_level` | string | 奖项筛选 | `特等奖` |
| `photo_type` | string | 照片类型 | `风光类` |
| `tag` | string | 标签筛选 | `银杏` |
| `search` | string | 关键词搜索 | `秋天` |
| `sort_by` | string | 排序字段 | `created_at` / `views` / `published_at` |

**响应**：
```json
{
  "items": [
    {
      "id": "photo-uuid",
      "filename": "银杏大道.jpg",
      "width": 4000,
      "height": 3000,
      "created_at": "2025-01-15T10:30:00",
      "classifications": {
        "season": {"node_name": "秋季"},
        "campus": {"node_name": "昌平校区"},
        "landmark": {"node_name": "图书馆"}
      }
    }
  ],
  "total": 542,
  "page": 1,
  "page_size": 30
}
```

### 获取单张照片详情

```http
GET /api/v1/photos/public/{photo_id}
```

### 获取照片缩略图

```http
GET /api/v1/photos/{photo_id}/image/thumbnail
```

**响应**：图片二进制数据（image/jpeg）

### 获取照片原图

```http
GET /api/v1/photos/{photo_id}/image/original
```

### 上传照片

```http
POST /api/v1/photos/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [图片文件]
```

---

## 🔍 搜索

### 向量语义搜索 ⭐ 新功能

```http
GET /api/v1/search
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `q` | string | ✅ | 搜索查询（自然语言） | `秋天的校园` |
| `limit` | int | ❌ | 返回数量（1-100） | `20` |
| `season` | string | ❌ | 季节过滤 | `秋季` |
| `campus` | string | ❌ | 校区过滤 | `昌平校区` |

**响应**：
```json
{
  "results": [
    {
      "photo_id": "d348b9f6-2203-5fcd-a6ca-de3cefb0c006",
      "score": 0.856,
      "tags": ["校名石碑", "草坪", "晚霞", "天空", "建筑"],
      "classifications": {
        "season": "秋季",
        "campus": "昌平校区",
        "landmark": "其它",
        "gallery_series": "昌平校区摄影大赛",
        "photo_type": "风光类"
      }
    }
  ],
  "total": 3,
  "query_time_ms": 251.76
}
```

**搜索示例**：

```bash
# 自然语言搜索
curl -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=秋天的校园" \
  --data-urlencode "limit=10"

# 带过滤条件
curl -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=建筑" \
  --data-urlencode "season=秋季" \
  --data-urlencode "campus=昌平校区"
```

**特点**：
- 基于向量相似度（bge-small-zh-v1.5 模型）
- 支持自然语言查询
- 返回相关度分数（0-1）
- 平均响应时间 ~200ms

---

## 🏷️ 标签管理

### 获取所有标签

```http
GET /api/v1/tags
```

**响应**：
```json
[
  {
    "id": 1,
    "name": "银杏",
    "category": "object",
    "usage_count": 45
  }
]
```

### 创建标签

```http
POST /api/v1/tags
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "新标签",
  "category": "scene"
}
```

### 标签类别

| 类别 | 说明 | 示例 |
|------|------|------|
| `scene` | 场景 | 校园、图书馆 |
| `object` | 物体 | 银杏、红砖 |
| `mood` | 情绪 | 温馨、宁静 |
| `style` | 风格 | 航拍、夜景 |
| `color` | 色彩 | 金色、蓝色 |

---

## 📂 分类系统

### 获取分类体系

```http
GET /api/v1/taxonomy/public
```

### 获取分类引导

```http
GET /api/v1/taxonomy/public/guide
```

**响应**：
```json
{
  "primary": ["gallery_series", "campus", "photo_type"],
  "dependencies": {
    "gallery_series": {
      "昌平校区摄影大赛": ["season", "award_level"]
    }
  }
}
```

---

## 📊 统计

### 获取统计概览

```http
GET /api/v1/stats/overview
Authorization: Bearer {token}
```

**响应**：
```json
{
  "total_photos": 542,
  "total_tags": 1156,
  "total_users": 15,
  "photos_this_month": 23
}
```

---

## 👤 用户管理

### 获取当前用户

```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

### 修改密码

```http
POST /api/v1/auth/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
  "old_password": "old_pass",
  "new_password": "new_pass"
}
```

---

## 🛠️ 管理员接口

### 用户管理

```http
GET    /api/v1/admin/users          # 获取用户列表
PUT    /api/v1/admin/users/{id}     # 更新用户信息
DELETE /api/v1/admin/users/{id}     # 删除用户
```

### 系统设置

```http
GET    /api/v1/admin/settings       # 获取设置
PUT    /api/v1/admin/settings       # 更新设置
```

### AI Provider 管理

```http
GET    /api/v1/admin/ai-providers   # 获取 AI 供应商列表
POST   /api/v1/admin/ai-providers   # 添加 AI 供应商
PUT    /api/v1/admin/ai-providers/{id}  # 更新
DELETE /api/v1/admin/ai-providers/{id}  # 删除
```

### 打标任务

```http
GET    /api/v1/tagging-tasks        # 获取任务列表
POST   /api/v1/tagging-tasks        # 创建打标任务
GET    /api/v1/tagging-tasks/{id}   # 获取任务详情
```

---

## 📝 错误码

| 状态码 | 说明 |
|--------|------|
| `200` | 成功 |
| `201` | 创建成功 |
| `400` | 请求参数错误 |
| `401` | 未授权（需要登录） |
| `403` | 禁止访问（权限不足） |
| `404` | 资源不存在 |
| `422` | 数据验证失败 |
| `500` | 服务器内部错误 |

---

## 🔧 开发说明

### 环境

- **后端**：FastAPI + Uvicorn（端口 8000）
- **数据库**：PostgreSQL 18
- **向量数据库**：Milvus（端口 19530）
- **对象存储**：MinIO（端口 9000）

### 本地测试

```bash
# 测试搜索 API
curl -G "http://127.0.0.1:8000/api/v1/search" \
  --data-urlencode "q=秋天" \
  --data-urlencode "limit=5"

# 测试公开照片
curl "http://127.0.0.1:8000/api/v1/photos/public?page_size=5"
```

### 相关文档

- [项目 README](../README.md)
- [运维指南](./AGENTS.md)
- [部署流程](./docs/SOP.md)
- [向量搜索计划](../visual-buct-vector-search-plan-v2.md)

---

*本文档由 Hermes Agent 自动生成*
