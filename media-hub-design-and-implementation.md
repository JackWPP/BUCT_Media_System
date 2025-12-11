# BUCT Media HUB 系统设计文档

## 1. 项目概述

### 1.1 项目目标

BUCT Media HUB 是基于现有 BUCT Tagger 系统的 Web 化升级版本，旨在将原有的本地脚本工作流转化为一个现代化的智能图片管理平台。系统保留原有的四阶段数据处理流程（预处理、分发、校验、入库），并通过 Web 界面提供更友好的交互体验。

### 1.2 核心设计原则

#### 本地优先开发策略
- 后端服务与前端应用均支持本机直接运行，便于快速迭代调试
- 数据库优先使用 SQLite，简化环境配置
- 文件存储先使用本地文件系统，待稳定后再考虑对象存储迁移
- Docker 容器化作为部署阶段的优化选项，非开发阶段必需

#### 展示优先设计理念
- 前端界面采用现代化设计语言，视觉效果精美专业
- 核心功能页面优先开发，确保展示效果
- 提供直观的数据可视化，清晰展现系统价值

### 1.3 系统定位与功能范围

**系统定位**：

BUCT Media HUB 是一个 **双端系统**：
- **后台管理系统（Admin）**：供管理员使用，用于内容导入、上传、审核、标签微调和上线管理
- **前台展示系统（Frontend）**：供师生访问，用于浏览、搜索、收藏和下载媒体资源

本设计文档重点关注 **后台管理系统** 的设计与实现。

**后台管理系统核心功能**：

1. **批量导入功能**
   - 导入现有打标系统生成的 JSON 数据包（包含图片和元数据）
   - 自动解析并入库到新系统数据库
   - 支持断点续传，避免重复导入

2. **单张/批量上传功能**
   - 上传若干张照片，自动调用 AI 打标服务
   - 实时显示 AI 分析进度和结果
   - 上传后照片进入"待审核"状态

3. **照片审核与管理**
   - 查看所有待审核、已上线、已下线的照片
   - 瀑布流展示，支持快速浏览
   - 批量操作：上线、下线、删除

4. **标签与属性微调**
   - 修改照片的季节、类别、校区等固定属性
   - 添加、删除、编辑关键词标签
   - 不区分 AI 标签和人工标签，统一管理
   - AI 的分析结果仅作为初始值，可随时修改

5. **搜索与筛选**
   - 按季节、类别、校区、关键词筛选
   - 按上传时间、拍摄时间排序
   - 按审核状态筛选

---

## 2. 系统架构设计

### 2.1 整体架构

系统采用前后端分离的三层架构，**后台管理系统**与**前台展示系统**共享同一套后端 API 和数据库。

```mermaid
graph TB
    subgraph "前端层"
        A[后台管理系统<br/>Admin Panel<br/>Port: 5173]
        B[前台展示系统<br/>Public Frontend<br/>Port: 5174]
    end
    
    subgraph "后端层 Backend API"
        C[FastAPI Server<br/>Port: 8000]
        D[AI 打标服务<br/>Ollama/Qwen-VL/LM Studio]
    end
    
    subgraph "数据层 Data"
        E[(SQLite DB<br/>buct_media.db)]
        F[本地文件存储<br/>uploads/ & library/]
    end
    
    A <-->|RESTful API| C
    B <-->|RESTful API| C
    C --> D
    C <--> E
    C <--> F
```

**架构说明**：
- **后台管理系统**：负责内容生产（上传、导入、审核、编辑）
- **前台展示系统**：负责内容消费（浏览、搜索、下载）
- **共享后端**：统一的 API 服务，通过权限控制区分管理员和普通用户
- **AI 服务**：支持本地部署（Ollama/LM Studio）或云端 API（DashScope）

### 2.2 技术栈选型

#### 前端技术栈
| 技术 | 版本 | 用途 | 选型理由 |
|------|------|------|----------|
| Vue 3 | 3.4+ | 核心框架 | Composition API + Script Setup 提供更好的逻辑复用 |
| Vite | 5.0+ | 构建工具 | 快速的开发服务器，毫秒级热更新 |
| TypeScript | 5.0+ | 类型系统 | 增强代码可维护性，减少运行时错误 |
| Pinia | 2.1+ | 状态管理 | 轻量级，TypeScript 友好 |
| Vue Router | 4.2+ | 路由管理 | 官方路由解决方案 |
| Naive UI | 2.38+ | UI 组件库 | 现代化设计，组件丰富，开箱即用 |
| TailwindCSS | 3.4+ | 样式框架 | 高度可定制，快速构建精美界面 |
| VueUse | 10.9+ | 工具库 | 提供丰富的组合式 API 工具函数 |
| Axios | 1.6+ | HTTP 客户端 | 请求拦截，自动处理 Token |

#### 后端技术栈
| 技术 | 版本 | 用途 | 选型理由 |
|------|------|------|----------|
| FastAPI | 0.109+ | Web 框架 | 异步高性能，自动生成 OpenAPI 文档 |
| Pydantic | 2.0+ | 数据验证 | 强类型校验，与 FastAPI 深度集成 |
| SQLAlchemy | 2.0+ | ORM 框架 | 支持异步操作，方便数据库迁移 |
| Alembic | 1.13+ | 数据库迁移 | 版本化管理数据库结构变更 |
| Pillow | 10.2+ | 图像处理 | 缩略图生成，EXIF 提取 |
| python-multipart | 0.0.9+ | 文件上传 | 处理 multipart/form-data |
| passlib | 1.7+ | 密码加密 | Bcrypt 哈希算法 |
| python-jose | 3.3+ | JWT 处理 | 生成与验证 Token |

---

## 3. 数据库设计

### 3.1 数据模型概览

系统数据模型在原有 BUCT Tagger 的 SQLite 表基础上进行扩展，支持多用户、任务分发等新功能。

```mermaid
erDiagram
    Users ||--o{ Photos : uploads
    Photos ||--o{ PhotoTags : has
    Tags ||--o{ PhotoTags : tagged_in
    
    Users {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        string role
        datetime created_at
        boolean is_active
    }
    
    Photos {
        uuid id PK
        uuid uploader_id FK
        string filename
        string original_path
        string processed_path
        string thumb_path
        int width
        int height
        string season
        string category
        string campus
        json exif_data
        string status
        string processing_status
        datetime created_at
        datetime captured_at
        datetime published_at
    }
    
    Tags {
        int id PK
        string name UK
        string category
        string color
        int usage_count
    }
    
    PhotoTags {
        uuid photo_id FK
        int tag_id FK
        datetime created_at
    }
```

### 3.2 核心表结构定义

#### Users 表 - 用户信息
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 登录邮箱 |
| hashed_password | VARCHAR(255) | NOT NULL | Bcrypt 哈希密码 |
| full_name | VARCHAR(100) | | 用户全名 |
| role | VARCHAR(20) | DEFAULT 'user' | 角色：admin / user |
| is_active | BOOLEAN | DEFAULT TRUE | 账号状态 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

**角色说明**：
- `admin`：管理员，可访问后台管理系统
- `user`：普通用户，仅可访问前台展示系统

#### Photos 表 - 照片资产
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键，对应原系统的 uuid |
| uploader_id | UUID | FK -> Users.id | 上传者（管理员） |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| original_path | TEXT | | 原始路径（用于追溯和导入） |
| processed_path | TEXT | | 处理后存储路径（library/Season/uuid.jpg） |
| thumb_path | TEXT | | 缩略图路径 |
| width | INTEGER | | 图片宽度 |
| height | INTEGER | | 图片高度 |
| season | VARCHAR(20) | | Spring / Summer / Autumn / Winter |
| category | VARCHAR(50) | | Landscape / Portrait / Activity / Documentary |
| campus | VARCHAR(50) | | 校区信息（东区/北区/西区/未知） |
| exif_data | JSON | | 完整 EXIF 元数据（包含 date_taken） |
| status | VARCHAR(20) | DEFAULT 'pending' | 照片状态 |
| processing_status | VARCHAR(20) | DEFAULT 'pending' | AI 处理状态 |
| created_at | DATETIME | DEFAULT NOW | 上传/导入时间 |
| captured_at | DATETIME | | 拍摄时间（从 EXIF 提取） |
| published_at | DATETIME | | 上线时间 |

**status 字段说明**：
- `pending`：待审核（刚上传或导入）
- `approved`：已审核通过，已上线
- `rejected`：已下线
- `deleted`：已删除（软删除）

**processing_status 字段说明**：
- `pending`：等待 AI 处理
- `processing`：AI 处理中
- `completed`：AI 处理完成
- `failed`：AI 处理失败
- `manual`：手动上传无需 AI 处理

#### Tags 表 - 标签库
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK AUTO_INCREMENT | 主键 |
| name | VARCHAR(100) | UNIQUE, NOT NULL | 标签名称（存储为小写） |
| category | VARCHAR(50) | | 标签分类：object / scene / color / mood |
| color | VARCHAR(7) | | 前端显示颜色（HEX 格式） |
| usage_count | INTEGER | DEFAULT 0 | 使用次数统计 |

#### PhotoTags 表 - 照片标签关联
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| photo_id | UUID | FK -> Photos.id | 照片 ID |
| tag_id | INTEGER | FK -> Tags.id | 标签 ID |
| created_at | DATETIME | DEFAULT NOW | 关联时间 |
| **PRIMARY KEY** | (photo_id, tag_id) | | 复合主键 |

**设计说明**：
- **移除 source 和 confidence 字段**：不再区分 AI 标签和人工标签
- AI 返回的 objects 数组直接作为初始标签，管理员可随时修改
- 标签来源信息不影响业务逻辑，简化数据模型

#### Tasks 表 - 任务管理
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| creator_id | UUID | FK -> Users.id | 创建者 |
| name | VARCHAR(200) | NOT NULL | 任务名称 |
| description | TEXT | | 任务描述 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending / in_progress / completed / archived |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| completed_at | DATETIME | | 完成时间 |

#### TaskPhotos 表 - 任务照片关联
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| task_id | UUID | FK -> Tasks.id | 任务 ID |
| photo_id | UUID | FK -> Photos.id | 照片 ID |
| verification_status | VARCHAR(20) | DEFAULT 'unverified' | unverified / verified / rejected |
| verified_at | DATETIME | | 校验时间 |
| **PRIMARY KEY** | (task_id, photo_id) | | 复合主键 |

### 3.3 索引策略

```sql
索引设计（提升查询性能）

Photos 表索引：
- idx_photos_owner_id ON Photos(owner_id)
- idx_photos_season ON Photos(season)
- idx_photos_category ON Photos(category)
- idx_photos_status ON Photos(processing_status)
- idx_photos_created_at ON Photos(created_at DESC)

PhotoTags 表索引：
- idx_phototags_tag_id ON PhotoTags(tag_id)
- idx_phototags_source ON PhotoTags(source)

Tags 表索引：
- idx_tags_category ON Tags(category)
- idx_tags_usage_count ON Tags(usage_count DESC)
```

---

## 4. 后端 API 设计

### 4.1 项目目录结构

```
buct_media_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── core/                      # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py              # 环境配置（Pydantic Settings）
│   │   ├── security.py            # JWT / 密码加密
│   │   ├── database.py            # 数据库连接与会话管理
│   │   └── deps.py                # 全局依赖注入
│   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── photo.py
│   │   ├── tag.py
│   │   └── task.py
│   ├── schemas/                   # Pydantic 数据模型（DTO）
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── photo.py
│   │   ├── tag.py
│   │   ├── task.py
│   │   └── token.py
│   ├── api/                       # API 路由
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # 路由聚合
│   │       └── endpoints/
│   │           ├── auth.py        # 登录/注册
│   │           ├── photos.py      # 照片上传/列表/详情
│   │           ├── tags.py        # 标签管理
│   │           └── tasks.py       # 任务管理
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── storage.py             # 文件存储服务
│   │   ├── ai_tagging.py          # AI 打标服务
│   │   ├── image_processing.py    # 图像处理（缩略图/EXIF）
│   │   └── task_manager.py        # 任务管理逻辑
│   ├── crud/                      # 数据库 CRUD 操作
│   │   ├── __init__.py
│   │   ├── base.py                # 基础 CRUD 类
│   │   ├── user.py
│   │   ├── photo.py
│   │   └── tag.py
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       └── exif.py                # EXIF 提取工具
├── alembic/                       # 数据库迁移
│   ├── versions/
│   └── env.py
├── uploads/                       # 本地上传文件目录
│   ├── originals/                 # 原图
│   └── thumbnails/                # 缩略图
├── tests/                         # 测试代码
├── .env.example                   # 环境变量示例
├── .env                           # 环境变量（不提交到 Git）
├── requirements.txt               # Python 依赖
├── alembic.ini                    # Alembic 配置
└── README.md
```

### 4.2 核心 API 端点设计

#### 4.2.1 认证模块 (auth.py)

| 端点 | 方法 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `/api/v1/auth/login` | POST | 用户登录 | `{email, password}` | `{access_token, token_type, user_info}` |
| `/api/v1/auth/me` | GET | 获取当前用户 | - | `{user_info}` |

#### 4.2.2 照片管理模块 (photos.py)

**上传与导入**

| 端点 | 方法 | 功能 | 请求 | 响应 |
|------|------|------|------|------|
| `/api/v1/photos/upload` | POST | 单张/批量上传照片 | `multipart/form-data: files[]` | `{uploaded_photos[]}` |
| `/api/v1/photos/import` | POST | 批量导入 JSON 数据包 | `{json_path, image_folder}` | `{imported_count, skipped_count}` |

**查询与管理**

| 端点 | 方法 | 功能 | 请求 | 响应 |
|------|------|------|------|------|
| `/api/v1/photos` | GET | 获取照片列表 | `?page=1&size=20&status=&season=&category=&tags=` | `{items[], total, page, size}` |
| `/api/v1/photos/{photo_id}` | GET | 获取照片详情 | - | `{photo_detail, tags[]}` |
| `/api/v1/photos/{photo_id}` | PATCH | 更新照片信息 | `{season, category, campus}` | `{updated_photo}` |
| `/api/v1/photos/{photo_id}` | DELETE | 删除照片（软删除） | - | `{message}` |

**审核操作**

| 端点 | 方法 | 功能 | 请求 | 响应 |
|------|------|------|------|------|
| `/api/v1/photos/{photo_id}/approve` | POST | 审核通过（上线） | - | `{updated_photo}` |
| `/api/v1/photos/{photo_id}/reject` | POST | 下线 | - | `{updated_photo}` |
| `/api/v1/photos/batch-approve` | POST | 批量上线 | `{photo_ids[]}` | `{updated_count}` |
| `/api/v1/photos/batch-reject` | POST | 批量下线 | `{photo_ids[]}` | `{updated_count}` |

**标签管理**

| 端点 | 方法 | 功能 | 请求 | 响应 |
|------|------|------|------|------|
| `/api/v1/photos/{photo_id}/tags` | POST | 添加标签 | `{tag_names[]}` | `{photo_tags[]}` |
| `/api/v1/photos/{photo_id}/tags/{tag_id}` | DELETE | 移除标签 | - | `{message}` |
| `/api/v1/photos/{photo_id}/tags` | PUT | 替换所有标签 | `{tag_names[]}` | `{photo_tags[]}` |

#### 4.2.3 标签库管理模块 (tags.py)

| 端点 | 方法 | 功能 | 请求 | 响应 |
|------|------|------|------|------|
| `/api/v1/tags` | GET | 获取标签列表 | `?search=&category=` | `{tags[]}` |
| `/api/v1/tags` | POST | 创建新标签 | `{name, category, color}` | `{tag}` |
| `/api/v1/tags/{tag_id}` | PATCH | 更新标签 | `{name, category, color}` | `{tag}` |
| `/api/v1/tags/{tag_id}` | DELETE | 删除标签 | - | `{message}` |
| `/api/v1/tags/popular` | GET | 获取热门标签 | `?limit=20` | `{tags[]}` |

### 4.3 核心业务流程设计

#### 4.3.1 批量导入流程（从现有打标系统）

这是将现有打标系统的数据迁移到 Web 系统的主要途径。

```mermaid
sequenceDiagram
    participant Admin as 管理员
    participant Frontend as 后台前端
    participant API as FastAPI
    participant DB as 数据库
    participant Storage as 文件存储
    
    Admin->>Frontend: 选择 JSON 文件或文件夹
    Frontend->>API: POST /photos/import
    API->>API: 递归扫描所有 .json 文件
    
    loop 每个 JSON 文件
        API->>API: 解析 JSON 数据
        
        loop 每个照片记录
            API->>DB: 检查 UUID 是否已存在
            
            alt UUID 不存在
                API->>Storage: 复制图片到 uploads/originals/
                API->>Storage: 生成缩略图到 uploads/thumbnails/
                API->>DB: 插入 Photos 记录 (status='pending')
                
                loop tags.keywords 数组
                    API->>DB: 在 Tags 表中查找或创建标签
                    API->>DB: 在 PhotoTags 表中创建关联
                end
            else UUID 已存在
                API->>API: 跳过（记录 skipped_count）
            end
        end
    end
    
    API-->>Frontend: 返回导入结果
    Frontend-->>Admin: 显示“导入完成：XX 张，跳过 YY 张”
```

**流程说明**：

1. **数据源选择**：管理员可以选择：
   - 单个 `pre_annotated.json` 或 `task_data.json`
   - 包含多个 JSON 的文件夹（系统会递归扫描）

2. **JSON 解析**：
   - 读取 JSON 数据，预期格式为数组：`[{uuid, filename, tags: {attributes, keywords, meta}}, ...]`
   - 支持 BUCT Tagger 的标准 JSON 格式

3. **重复检查**：
   - 使用 UUID 作为唯一标识，检查 Photos 表
   - 如果已存在，跳过该记录（支持断点续传）

4. **文件处理**：
   - 根据 `original_path` 查找图片文件
   - 智能路径解析：尝试绝对路径 -> JSON 同级目录 -> images/ 子目录
   - 复制到 `uploads/originals/{uuid}.jpg`
   - 生成缩略图保存到 `uploads/thumbnails/{uuid}_thumb.jpg`

5. **元数据入库**：
   - 提取 `tags.attributes.season` 和 `category` 直接存入 Photos 表
   - 提取 `tags.meta` 作为 JSONB 存入 exif_data 字段
   - 初始 status 为 `pending`，processing_status 为 `manual`（已经打过标）

6. **标签处理**：
   - 遍历 `tags.keywords` 数组
   - 对每个关键词，在 Tags 表中查找（name 小写匹配）
   - 如果不存在，创建新标签并分配随机颜色
   - 在 PhotoTags 表中建立关联

#### 4.3.2 单张/批量上传流程（带 AI 自动打标）

```mermaid
sequenceDiagram
    participant Admin as 管理员
    participant Frontend as 后台前端
    participant API as FastAPI
    participant Storage as 文件存储
    participant DB as 数据库
    participant AI as AI 服务
    
    Admin->>Frontend: 选择多张图片上传
    Frontend->>API: POST /photos/upload (multipart files)
    API->>API: 验证文件类型与大小
    
    loop 每个文件
        API->>API: 生成 UUID
        API->>Storage: 保存原图到 uploads/originals/
        API->>API: 提取 EXIF 信息
        API->>Storage: 生成缩略图到 uploads/thumbnails/
        
        API->>DB: 插入 Photo 记录
        Note over DB: status='pending'<br/>processing_status='pending'
        DB-->>API: 返回 photo_id
        
        API->>AI: 添加后台任务 analyze_photo(photo_id)
    end
    
    API-->>Frontend: 返回上传成功响应
    Frontend-->>Admin: 显示"上传成功，AI 分析中..."
    
    Note over AI: 后台异步执行
    AI->>DB: 更新 processing_status='processing'
    AI->>Storage: 读取图片
    AI->>AI: 压缩图片至 1024px
    AI->>AI: 调用 VLM（使用标准 Prompt）
    AI->>AI: 解析 JSON 响应
    
    AI->>DB: 更新 Photos 表 (season, category)
    
    loop objects 数组
        AI->>DB: 查找或创建 Tag
        AI->>DB: 创建 PhotoTags 关联
    end
    
    AI->>DB: 更新 processing_status='completed'
    
    Frontend->>API: 轮询 GET /photos/{photo_id}
    API-->>Frontend: 返回更新后的照片信息
    Frontend-->>Admin: 刷新界面，显示 AI 生成的标签
```

**流程说明**：

1. **文件接收与校验**：
   - 验证文件扩展名（jpg/png/webp）
   - 验证文件大小（例如最大 20MB）

2. **同步处理**：
   - 生成 UUID v4
   - 保存原图到 `uploads/originals/{uuid}.jpg`
   - 使用 Pillow 提取 EXIF（date_taken, 相机型号等）
   - 生成缩略图（400px 宽）保存到 `uploads/thumbnails/{uuid}_thumb.jpg`
   - 写入数据库 Photos 表，初始状态 `status='pending'`, `processing_status='pending'`

3. **异步 AI 处理**：
   - 通过 FastAPI 的 BackgroundTasks 触发 AI 打标任务
   - 读取图片，压缩至 1024px 减少 Token 消耗
   - 调用本地 Ollama/LM Studio 或云端 DashScope API
   - 使用标准 Prompt（与现有系统一致）

4. **结果处理**：
   - 解析 AI 返回的 JSON：`{season, category, objects}`
   - 更新 Photos 表的 season 和 category 字段
   - 遍历 objects 数组，创建标签关联
   - 更新 processing_status 为 `completed`

5. **前端更新**：
   - 使用轮询机制（每 2 秒）检查 processing_status
   - 当状态变为 `completed` 时，刷新照片信息展示 AI 标签

#### 4.3.3 照片审核与微调流程

**审核操作**：

1. **单张审核**：
   - 管理员点击“审核通过”按钮
   - 调用 `POST /photos/{photo_id}/approve`
   - 更新 status 为 `approved`，设置 published_at 为当前时间
   - 前台展示系统可以查询到该照片

2. **批量审核**：
   - 管理员选中多张照片
   - 调用 `POST /photos/batch-approve` 传递 photo_ids 数组
   - 后端批量更新数据库

**微调操作**：

1. **修改属性**：
   - 管理员在详情页修改 season/category/campus
   - 调用 `PATCH /photos/{photo_id}` 更新对应字段

2. **编辑标签**：
   - 添加标签：`POST /photos/{photo_id}/tags` 传递 `{tag_names: ["教学楼", "樱花"]}`
   - 删除标签：`DELETE /photos/{photo_id}/tags/{tag_id}`
   - 替换全部标签：`PUT /photos/{photo_id}/tags` 传递新的完整标签列表

3. **标签自动完成**：
   - 前端输入框支持搜索已有标签
   - 调用 `GET /tags?search=keyword` 获取匹配结果
   - 显示下拉建议列表

**服务职责**：
- 调用视觉语言模型（VLM）对图片进行内容识别
- 解析 AI 返回结果，提取结构化标签
- 与数据库交互，存储标签关联关系

**Prompt 设计策略**：

系统使用的标准 Prompt 模板（与现有 BUCT Tagger 保持一致）：

```
请分析这张图片。

1. 判断季节 (Spring/Summer/Autumn/Winter)。

2. 判断场景类型 (Landscape/Portrait/Activity/Documentary)。

3. 提取画面中的关键物体 (不超过5个) 使用中文标签。

请以纯JSON格式返回，不要包含Markdown格式标记，格式如下:

{
    "season": "...",
    "category": "...",
    "objects": ["...", "..."]
}
```

**AI 返回示例**：
```json
{
    "season": "Winter",
    "category": "Landscape",
    "objects": ["砖墙", "建筑", "门", "天空", "雪花"]
}
```

**标签归一化处理**：
- 从 AI 返回的 JSON 中提取 `objects` 数组作为关键词标签
- 提取 `season` 和 `category` 填充到 Photos 表的对应字段
- 将 `objects` 中的每个关键词转换为小写存储
- 去重并检查 Tags 表中是否已存在该标签
- 若为新标签，自动创建并分配随机颜色
- 在 PhotoTags 表中建立关联，标记 `source='ai'`

---

## 5. 前端界面设计

### 5.1 项目目录结构

```
buct_media_frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── assets/                    # 静态资源
│   │   ├── images/
│   │   └── styles/
│   │       └── global.css         # 全局样式
│   ├── components/                # 通用组件
│   │   ├── common/
│   │   │   ├── AppHeader.vue      # 顶部导航栏
│   │   │   ├── AppSidebar.vue     # 侧边栏
│   │   │   └── LoadingSpinner.vue # 加载动画
│   │   ├── photo/
│   │   │   ├── PhotoCard.vue      # 照片卡片
│   │   │   ├── PhotoGrid.vue      # 瀑布流网格
│   │   │   ├── PhotoDetail.vue    # 照片详情模态框
│   │   │   ├── PhotoUploader.vue  # 上传组件
│   │   │   └── TagInput.vue       # 标签输入框
│   │   └── task/
│   │       ├── TaskCard.vue
│   │       └── TaskVerifier.vue
│   ├── views/                     # 页面视图
│   │   ├── auth/
│   │   │   ├── LoginView.vue
│   │   │   └── RegisterView.vue
│   │   ├── gallery/
│   │   │   ├── GalleryView.vue    # 主画廊页面
│   │   │   └── PhotoDetailView.vue
│   │   ├── upload/
│   │   │   └── UploadView.vue
│   │   ├── tasks/
│   │   │   ├── TaskListView.vue
│   │   │   └── TaskDetailView.vue
│   │   └── admin/
│   │       └── TagManageView.vue
│   ├── stores/                    # Pinia 状态管理
│   │   ├── auth.ts                # 用户认证状态
│   │   ├── photo.ts               # 照片列表状态
│   │   ├── tag.ts                 # 标签库状态
│   │   └── upload.ts              # 上传队列状态
│   ├── services/                  # API 服务封装
│   │   ├── api.ts                 # Axios 实例配置
│   │   ├── auth.service.ts
│   │   ├── photo.service.ts
│   │   ├── tag.service.ts
│   │   └── task.service.ts
│   ├── router/                    # 路由配置
│   │   └── index.ts
│   ├── types/                     # TypeScript 类型定义
│   │   ├── user.ts
│   │   ├── photo.ts
│   │   └── tag.ts
│   ├── utils/                     # 工具函数
│   │   ├── format.ts              # 日期/文件大小格式化
│   │   └── validate.ts            # 表单验证
│   ├── App.vue                    # 根组件
│   └── main.ts                    # 应用入口
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── README.md
```

### 5.2 核心页面设计

#### 5.2.1 登录页面 (LoginView.vue)

**设计要点**：
- 居中卡片式布局，背景使用校园风景渐变图
- 表单包含邮箱、密码输入框
- 记住登录状态复选框
- 登录按钮带加载状态动画
- 底部提供注册跳转链接

**视觉风格**：
- 主色调：深蓝色（#1e3a8a）+ 渐变背景
- 卡片：白色背景，圆角阴影，玻璃拟态效果
- 输入框：聚焦时边框蓝色高亮动画

#### 5.2.2 主画廊页面 (GalleryView.vue)

**布局结构**：

```
+--------------------------------------------------+
| Header: Logo | 搜索框 | 上传按钮 | 用户头像         |
+----------+-------------------------------------------+
| Sidebar  |   Main Content Area                      |
| - 全部   |   +----------------------------------+   |
| - 春季   |   |  瀑布流照片网格                  |   |
| - 夏季   |   |  (虚拟滚动，无限加载)            |   |
| - 秋季   |   |                                  |   |
| - 冬季   |   +----------------------------------+   |
| -------- |                                          |
| - 风景   |   加载更多指示器                         |
| - 人像   |                                          |
| - 活动   |                                          |
| - 纪实   |                                          |
+----------+------------------------------------------+
```

**核心功能**：
- **顶部搜索栏**：支持标签、文件名、日期范围搜索，提供搜索建议
- **侧边栏筛选**：按季节、分类、校区快速筛选
- **瀑布流网格**：
  - 使用 CSS Grid 或 `vue-masonry-wall` 实现
  - 每张照片卡片显示：缩略图、文件名、标签（最多 3 个）
  - 悬停效果：放大、显示更多操作按钮（编辑/删除/下载）
- **虚拟滚动**：滚动到底部自动加载下一页（Infinite Scroll）
- **批量操作**：选中多张照片后可批量打标、删除、添加到任务

**照片卡片设计**：
```
+--------------------+
|   [缩略图]         |
|   (16:9 裁剪)      |
+--------------------+
| 文件名.jpg         |
| 标签1 标签2 标签3  |
| 📅 2024-03-20      |
+--------------------+
```

#### 5.2.3 照片详情模态框 (PhotoDetail.vue)

**触发方式**：点击画廊中的照片卡片

**布局**：
```
+---------------------------------------------------------------+
|  [关闭按钮]                                         [操作菜单] |
|                                                                 |
|  +----------------------------+  +---------------------------+ |
|  |                            |  |  基本信息                 | |
|  |   高清大图                 |  |  - 文件名                 | |
|  |   (支持缩放/旋转)          |  |  - 尺寸: 4032x3024        | |
|  |                            |  |  - 大小: 5.2 MB           | |
|  |                            |  |  - 拍摄时间               | |
|  |                            |  |  - 相机型号               | |
|  +----------------------------+  +---------------------------+ |
|                                  |  分类属性                 | |
|                                  |  季节: [Spring ▼]         | |
|                                  |  类别: [Landscape ▼]      | |
|                                  |  校区: [North ▼]          | |
|  [← 上一张]          [下一张 →]  +---------------------------+ |
|                                  |  标签管理                 | |
|                                  |  AI 标签 (灰色虚线框):    | |
|                                  |    教学楼 樱花 蓝天       | |
|                                  |  人工标签 (蓝色实线框):   | |
|                                  |    北辰校区 春季          | |
|                                  |  + 添加新标签             | |
|                                  +---------------------------+ |
+---------------------------------------------------------------+
```

**交互特性**：
- 左右箭头键快速切换上下张照片
- 标签点击可跳转至该标签的搜索结果
- AI 标签可通过点击转换为人工确认标签
- 支持直接编辑季节、类别等属性，实时保存

#### 5.2.4 上传页面 (UploadView.vue)

**核心组件：PhotoUploader.vue**

**功能设计**：
- 拖拽上传区域（Drag & Drop）
- 点击选择文件（支持多选）
- 实时预览待上传图片列表
- 显示每张图片的上传进度条
- 支持移除队列中的图片
- 上传完成后展示缩略图和 AI 打标状态

**上传队列展示**：
```
+-----------------------------------------------------------+
|  拖拽文件到此处 或 点击选择文件                            |
|  支持 JPG, PNG, WEBP 格式，单个文件最大 20MB               |
+-----------------------------------------------------------+
|  待上传列表：                                              |
|  +-------------------------------------------------------+ |
|  | [缩略图] IMG_001.jpg  5.2MB   [████████--] 80%  [×]  | |
|  | [缩略图] IMG_002.jpg  3.1MB   [完成]            [×]  | |
|  | [缩略图] IMG_003.jpg  8.5MB   [等待中]          [×]  | |
|  +-------------------------------------------------------+ |
|  总计: 3 张 | 已上传: 1 张 | 失败: 0 张                     |
|  [开始上传] [清空队列]                                      |
+-----------------------------------------------------------+
```

**上传后处理**：
- 显示"AI 正在分析中..."加载动画
- 完成后弹出提示："已成功上传 3 张照片，AI 标签已生成"
- 提供"前往查看"按钮跳转至画廊

### 5.3 视觉设计规范

#### 色彩方案

| 用途 | 颜色值 | 说明 |
|------|--------|------|
| 主色 | #1e3a8a | 深蓝色（校园主题） |
| 辅助色 | #3b82f6 | 亮蓝色（按钮、链接） |
| 成功 | #10b981 | 绿色（完成状态） |
| 警告 | #f59e0b | 橙色（处理中） |
| 错误 | #ef4444 | 红色（失败） |
| 背景 | #f9fafb | 浅灰色（页面背景） |
| 卡片 | #ffffff | 白色（内容卡片） |
| 文本主 | #111827 | 深灰色 |
| 文本次 | #6b7280 | 中灰色 |
| AI 标签 | #fef3c7 | 淡黄色背景 + #92400e 边框（虚线） |
| 人工标签 | #dbeafe | 淡蓝色背景 + #1e40af 边框（实线） |

#### 组件样式规范

**按钮**：
- 主按钮：蓝色背景，白色文字，悬停加深，圆角 0.5rem
- 次要按钮：白色背景，蓝色边框，悬停浅蓝背景
- 危险按钮：红色背景，白色文字

**卡片**：
- 圆角：0.75rem
- 阴影：shadow-lg（悬停时 shadow-xl）
- 边框：1px solid #e5e7eb

**标签 Tag**：
- 圆角：9999px（胶囊形）
- 内边距：0.25rem 0.75rem
- 字体大小：0.875rem
- 可移除标签：右侧显示 × 图标

**输入框**：
- 边框：1px solid #d1d5db
- 聚焦时：边框变蓝，外发光效果
- 圆角：0.5rem

### 5.4 响应式设计

| 断点 | 屏幕宽度 | 布局调整 |
|------|----------|----------|
| Mobile | < 640px | 隐藏侧边栏，顶部添加抽屉菜单；瀑布流 1 列 |
| Tablet | 640px - 1024px | 侧边栏可折叠；瀑布流 2-3 列 |
| Desktop | > 1024px | 完整布局；瀑布流 4-5 列 |

---

## 6. 核心功能实现策略

### 6.1 瀑布流布局实现

**技术方案**：使用 CSS Grid + 自定义逻辑

**实现步骤**：
1. 获取照片列表数据（包含宽高信息）
2. 计算每张图片在固定宽度下的高度
3. 使用 CSS Grid 的 `grid-template-columns` 和 `grid-row-end` 动态布局
4. 监听窗口 resize 事件，重新计算布局

**备选方案**：使用 `vue-masonry-wall` 库（开箱即用，性能优化好）

### 6.2 虚拟滚动与无限加载

**实现原理**：
- 监听滚动事件，当距离底部 < 200px 时触发加载
- 前端维护当前页码，每次请求下一页数据
- 追加到现有列表中，避免整体重新渲染

**优化策略**：
- 使用 `IntersectionObserver` 替代 scroll 事件监听（性能更好）
- 防抖处理，避免重复请求
- 使用 `vue-virtual-scroller` 处理超大列表（DOM 节点回收）

### 6.3 文件上传与进度显示

**技术实现**：
- 使用 Axios 的 `onUploadProgress` 回调获取上传进度
- FormData 封装多文件上传
- 后端使用 FastAPI 的 `UploadFile` 流式接收

**示例流程**：
```typescript
上传逻辑伪代码

async function uploadPhotos(files: File[]) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await axios.post('/api/v1/photos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      updateProgressBar(percentCompleted);  // 更新进度条
    }
  });
  
  return response.data;
}
```

### 6.4 实时 AI 打标状态更新

**方案一：前端轮询**（MVP 推荐）
- 上传后每隔 2 秒请求照片详情接口
- 检查 `processing_status` 是否变为 `completed`
- 完成后停止轮询，刷新标签列表

**方案二：WebSocket 推送**（进阶版）
- 后端 AI 任务完成后通过 WebSocket 推送事件
- 前端监听事件，实时更新界面
- 需要额外集成 Socket.IO 或 FastAPI WebSocket

### 6.5 标签输入与自动完成

**组件设计**：TagInput.vue

**功能特性**：
- 输入时实时搜索标签库（防抖 300ms）
- 下拉显示匹配的已有标签
- 支持创建新标签（输入后按回车）
- 已选标签以胶囊形式展示，可点击删除

**数据交互示例**：
```typescript
// 标签搜索（防抖处理）
const searchTags = useDebounceFn(async (query: string) => {
  if (query.length < 2) return;
  const results = await tagService.searchTags(query);
  suggestions.value = results;
}, 300);
```

### 6.6 AI 数据流与 JSON 结构

**BUCT Tagger 数据格式兼容性说明**：

系统完全兼容现有 BUCT Tagger 的数据格式，JSON 结构示例：

```json
{
  "uuid": "62d59449-3aad-4a61-adda-937459eb0be2",
  "filename": "1765016943275.png",
  "original_path": "D:\\bqb_pic_project\\image\\README\\1765016943275.png",
  "processed_path": "",
  "thumb_path": "",
  "width": 2560,
  "height": 1369,
  "tags": {
    "attributes": {
      "season": "Winter",
      "category": "Landscape"
    },
    "keywords": [
      "砖墙",
      "建筑",
      "门",
      "天空",
      "雪花"
    ],
    "meta": {}
  }
}
```

**AI 分析完整流程**：

1. **用户上传图片**：前端发送图片文件到后端

2. **后端处理**：
   - 保存原图到 `uploads/originals/{uuid}.jpg`
   - 生成缩略图到 `uploads/thumbnails/{uuid}_thumb.jpg`
   - 提取图片宽高信息
   - 初始化 Photo 记录（status='pending'）

3. **AI 推理调用**（后台任务）：
   ```python
   # 使用标准 Prompt
   prompt = """请分析这张图片。
   
   1. 判断季节 (Spring/Summer/Autumn/Winter)。
   
   2. 判断场景类型 (Landscape/Portrait/Activity/Documentary)。
   
   3. 提取画面中的关键物体 (不超过5个) 使用中文标签。
   
   请以纯JSON格式返回，不要包含Markdown格式标记，格式如下:
   
   {
       "season": "...",
       "category": "...",
       "objects": ["...", "..."]
   }"""
   ```

4. **AI 返回示例**：
   ```json
   {
     "season": "Winter",
     "category": "Landscape",
     "objects": ["砖墙", "建筑", "门", "天空", "雪花"]
   }
   ```

5. **后端数据处理**：
   - 更新 Photos 表：`season='Winter'`, `category='Landscape'`
   - 遍历 `objects` 数组，为每个关键词：
     - 在 Tags 表中查找或创建标签（name 转小写存储）
     - 在 PhotoTags 表创建关联，标记 `source='ai'`
   - 更新 Photo 状态为 `completed`

6. **前端展示**：
   - 查询该照片的所有标签
   - AI 标签显示为淡黄色背景+虚线边框
   - 用户可点击 AI 标签转为人工确认标签（更新 source='manual'）

**数据库与 JSON 的映射关系**：

| JSON 字段 | 数据库表 | 字段/操作 |
|-----------|----------|----------|
| `uuid` | Photos | id (主键) |
| `filename` | Photos | filename |
| `original_path` | Photos | original_path |
| `width`, `height` | Photos | width, height |
| `tags.attributes.season` | Photos | season |
| `tags.attributes.category` | Photos | category |
| `tags.keywords[]` | Tags + PhotoTags | 遍历创建标签关联 |
| `tags.meta` | Photos | exif_data (JSON 字段) |

---

## 7. 本地开发环境配置

### 7.1 后端启动步骤

#### 环境准备
```bash
Python 版本要求：3.10+

步骤 1：创建虚拟环境
cd buct_media_backend
python -m venv venv

步骤 2：激活虚拟环境
Windows: venv\Scripts\activate
macOS/Linux: source venv/bin/activate

步骤 3：安装依赖
pip install -r requirements.txt

步骤 4：配置环境变量
复制 .env.example 为 .env，修改以下关键配置：
DATABASE_URL=sqlite:///./buct_media.db
UPLOAD_DIR=./uploads
OLLAMA_API_URL=http://localhost:11434  # 若使用 Ollama

步骤 5：初始化数据库
alembic upgrade head  # 执行数据库迁移

步骤 6：创建管理员用户（可选）
python scripts/create_admin.py

步骤 7：启动开发服务器
uvicorn app.main:app --reload --port 8000

访问：http://localhost:8000/docs（FastAPI 自动生成的 Swagger 文档）
```

#### 本地 AI 服务配置（可选）

**使用 Ollama（推荐）**：
```bash
安装 Ollama（macOS/Linux）
curl -fsSL https://ollama.com/install.sh | sh

Windows 用户下载安装包：https://ollama.com/download

拉取 LLaVA 模型
ollama pull llava

启动服务（默认端口 11434）
ollama serve
```

**测试 AI 服务**：
```bash
curl http://localhost:11434/api/tags
应返回已安装的模型列表
```

### 7.2 前端启动步骤

```bash
Node.js 版本要求：18+

步骤 1：安装依赖
cd buct_media_frontend
npm install

步骤 2：配置 API 地址
编辑 .env.development 文件：
VITE_API_BASE_URL=http://localhost:8000

步骤 3：启动开发服务器
npm run dev

访问：http://localhost:5173
```

### 7.3 完整开发环境检查清单

| 服务 | 地址 | 状态检查 |
|------|------|----------|
| 后端 API | http://localhost:8000 | 访问 /docs 查看 API 文档 |
| 前端界面 | http://localhost:5173 | 浏览器打开主页 |
| 数据库 | ./buct_media.db | 使用 DB Browser for SQLite 查看 |
| AI 服务 | http://localhost:11434 | curl 测试或暂时跳过 |
| 文件存储 | ./uploads/ | 确保目录存在且有写权限 |

---

## 8. 数据迁移与兼容性

### 8.1 从现有 BUCT Tagger 迁移数据

**迁移脚本设计**：`scripts/migrate_from_tagger.py`

**迁移流程**：
1. 读取现有的 `buct_gallery.db` 数据库
2. 遍历 `photos` 表中的所有记录
3. 解析 JSON 格式的 `keywords` 和 `meta` 字段
4. 在新数据库中创建对应的 Photo 记录
5. 提取 keywords，在 Tags 表中创建或查找标签
6. 在 PhotoTags 表中建立关联关系（source='manual'）
7. 复制图片文件到新的 uploads 目录

**数据映射关系**：
```
旧数据库字段映射

photos.uuid -> Photos.id
photos.filename -> Photos.filename
photos.original_path -> Photos.original_path
photos.processed_path -> Photos.processed_path（按 season 分类存储）
photos.width -> Photos.width
photos.height -> Photos.height
photos.season -> Photos.season
photos.category -> Photos.category
photos.campus -> Photos.campus
photos.keywords (JSON) -> 解析后创建 PhotoTags 关系
photos.meta (JSON) -> Photos.exif_data
photos.created_at -> Photos.created_at
```

### 8.2 文件组织结构调整

**原有结构**：
```
Library_Root/
└── Spring/
    └── {uuid}.jpg
```

**新结构**：
```
uploads/
├── originals/
│   └── {uuid}.jpg
└── thumbnails/
    └── {uuid}_thumb.jpg
```

**迁移策略**：保留原有路径记录，新上传文件使用新结构

---

## 9. 测试策略

### 9.1 后端测试

**测试框架**：pytest + httpx

**测试覆盖范围**：
- 单元测试：各 CRUD 操作、工具函数
- 集成测试：API 端点完整流程
- 性能测试：大文件上传、并发请求

**示例测试用例**：
```python
测试照片上传 API

async def test_upload_photo(client, auth_headers):
    files = {'files': open('test_image.jpg', 'rb')}
    response = await client.post('/api/v1/photos/upload', files=files, headers=auth_headers)
    assert response.status_code == 200
    assert 'id' in response.json()[0]
```

### 9.2 前端测试

**测试框架**：Vitest + Vue Test Utils

**测试重点**：
- 组件渲染测试
- 用户交互测试（点击、输入）
- API 调用模拟（Mock）

### 9.3 端到端测试

**工具**：Playwright

**测试场景**：
- 用户登录 -> 上传照片 -> 查看画廊 -> 编辑标签 -> 搜索

---

## 10. 部署与扩展规划

### 10.1 Docker 容器化（第二阶段）

**容器编排文件**：docker-compose.yml

**服务划分**：
- `backend`：FastAPI 应用
- `frontend`：Nginx 托管静态文件
- `db`：PostgreSQL（替代 SQLite）
- `minio`：MinIO 对象存储（替代本地文件系统）
- `ollama`：AI 推理服务

### 10.2 性能优化方向

**前端优化**：
- 代码分割（Code Splitting）：路由级别懒加载
- 图片懒加载：使用 `loading="lazy"` 或 Intersection Observer
- CDN 加速：静态资源托管到 CDN
- Service Worker：离线缓存

**后端优化**：
- 数据库索引优化
- Redis 缓存热门查询结果
- 图片 CDN 分发
- 异步任务队列（Celery + Redis）

### 10.3 功能扩展方向

**近期规划**：
- 批量编辑功能
- 导出功能（ZIP 打包下载）
- 用户权限管理（角色分级）
- 操作日志记录

**长期规划**：
- 语义搜索（CLIP 模型 + 向量数据库）
- 人脸识别与聚类
- 视频素材支持
- 移动端 App

---

## 11. 风险评估与应对

### 11.1 技术风险

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|----------|
| AI 模型推理速度慢 | 用户体验差 | 中 | 使用轻量级模型（Moondream）；提供手动打标选项 |
| 大文件上传失败 | 功能不可用 | 中 | 实现断点续传；限制单文件大小 |
| 数据库性能瓶颈 | 系统卡顿 | 低 | 建立索引；分页查询；考虑迁移到 PostgreSQL |
| 前端渲染性能问题 | 浏览器崩溃 | 中 | 虚拟滚动；图片懒加载；缩略图优化 |

### 11.2 时间风险

**开发周期估算**：

| 阶段 | 预计时间 | 关键里程碑 |
|------|----------|------------|
| 后端基础搭建 | 1 周 | 完成数据库设计、基础 CRUD API |
| 前端框架搭建 | 1 周 | 完成路由、状态管理、UI 组件库集成 |
| 核心功能开发 | 2-3 周 | 上传、画廊、详情、标签功能可用 |
| AI 服务集成 | 1 周 | 自动打标功能上线 |
| 界面美化与优化 | 1 周 | 完成视觉设计，准备展示 |
| 测试与修复 | 1 周 | Bug 修复，性能优化 |

**总计**：7-9 周（可根据实际情况调整优先级）

---

## 12. 项目交付物

### 12.1 代码仓库结构

```
BUCT_Media_System/
├── backend/                    # 后端代码
├── frontend/                   # 前端代码
├── docs/                       # 文档
│   ├── API.md                  # API 接口文档
│   ├── DATABASE.md             # 数据库设计文档
│   └── DEPLOYMENT.md           # 部署指南
├── scripts/                    # 工具脚本
│   ├── migrate_from_tagger.py  # 数据迁移脚本
│   └── create_admin.py         # 创建管理员用户
├── docker-compose.yml          # Docker 编排文件（可选）
├── README.md                   # 项目说明
└── .gitignore
```

### 12.2 文档清单

- 系统设计文档（本文档）
- API 接口文档（Swagger 自动生成 + 补充说明）
- 数据库设计文档（ERD + 表结构说明）
- 本地开发环境配置指南
- Docker 部署指南（第二阶段）
- 用户操作手册（截图 + 流程说明）

### 12.3 演示准备

**展示内容建议**：
1. **登录页面**：展示精美的 UI 设计
2. **上传功能**：拖拽上传 -> 进度条 -> AI 打标动画
3. **画廊浏览**：瀑布流布局 -> 流畅滚动 -> 点击查看大图
4. **标签管理**：AI 标签与人工标签对比 -> 标签搜索与添加
5. **搜索筛选**：按季节、类别快速筛选展示
6. **数据统计**：展示图片总数、标签分布等数据可视化（可选）

**演示数据准备**：
- 准备 50-100 张高质量校园图片
- 预先上传并确保 AI 打标完成
- 覆盖四季、多种类别的样本数据

---

## 附录 A：环境变量配置示例

### 后端 .env 文件
```ini
后端环境变量

应用配置
APP_NAME=BUCT Media HUB
APP_VERSION=1.0.0
DEBUG=True

数据库配置
DATABASE_URL=sqlite:///./buct_media.db
本地开发使用 SQLite
生产环境可切换为：postgresql://user:pass@localhost/dbname

文件存储配置
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=20971520  # 20MB in bytes

安全配置
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

AI 服务配置
OLLAMA_API_URL=http://localhost:11434
AI_MODEL_NAME=llava
AI_ENABLED=True  # 设为 False 可禁用 AI 功能

CORS 配置
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 前端 .env.development 文件
```ini
前端环境变量（开发环境）

VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=BUCT Media HUB
VITE_MAX_UPLOAD_SIZE=20  # MB
```

---

## 附录 B：关键技术参考资料

### 后端相关
- FastAPI 官方文档：https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 文档：https://docs.sqlalchemy.org/
- Pydantic V2 文档：https://docs.pydantic.dev/
- Ollama API 文档：https://github.com/ollama/ollama/blob/main/docs/api.md

### 前端相关
- Vue 3 官方文档：https://vuejs.org/
- Naive UI 组件库：https://www.naiveui.com/
- TailwindCSS 文档：https://tailwindcss.com/
- VueUse 工具库：https://vueuse.org/

### 工具与最佳实践
- Alembic 数据库迁移：https://alembic.sqlalchemy.org/
- Axios HTTP 客户端：https://axios-http.com/
- Vue Masonry Wall：https://github.com/DerYeger/yeger/tree/main/packages/vue-masonry-wall

---

## 结语

本设计文档为 BUCT Media HUB 项目提供了完整的技术架构和实施路线图。核心设计理念是：

1. **渐进式开发**：从本地开发环境起步，代码调试稳定后再考虑容器化部署
2. **展示优先**：前端界面设计精美，核心功能完善，确保能够有效展示系统价值
3. **架构可扩展**：虽然 MVP 阶段使用 SQLite 和本地文件系统，但数据模型和服务层设计已预留扩展空间，未来可平滑迁移到 PostgreSQL + MinIO 的生产架构
4. **保留现有优势**：继承 BUCT Tagger 的数据模式和工作流精髓，确保业务连续性

建议开发顺序：后端 API（1-2 周）→ 前端基础页面（1 周）→ 上传与画廊功能（1 周）→ AI 集成（1 周）→ 界面美化（1 周），总计 5-7 周可完成可展示版本。
