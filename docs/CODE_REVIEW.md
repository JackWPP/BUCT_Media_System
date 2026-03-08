# BUCT Media System - 代码审查报告

**审查日期**: 2026-03-02  
**审查范围**: 后端 (FastAPI)、前端 (Vue 3)、部署配置  
**风险等级**: 🔴 高 (生产部署需修复)

---

## 📋 执行摘要

### 现状评估
- ✅ **架构合理** - FastAPI + Vue 3 + SQLAlchemy 2.0 技术选型恰当
- ✅ **功能完整** - MVP 阶段功能覆盖完善（上传、AI打标、审核、权限）
- ✅ **异步支持** - 后端全异步设计，性能基础良好
- 🟡 **生产就绪度** - 60% (需要解决关键安全和配置问题)

### 关键问题（需立即修复）
| 序号 | 问题 | 严重程度 | 修复时间 |
|------|------|--------|--------|
| 1 | SECRET_KEY 硬编码默认值 | 🔴 高 | 5分钟 |
| 2 | DEBUG=True 在生产配置 | 🔴 高 | 2分钟 |
| 3 | 文件上传缺少类型校验 | 🔴 高 | 30分钟 |
| 4 | CORS 配置过宽 | 🟡 中 | 10分钟 |
| 5 | 前端 API 路由路径错误 | 🔴 高 | ✅ 已修复 |

---

## 🔐 安全性分析

### 1. 密钥管理 🔴 高风险

**问题位置**: `backend/app/core/config.py:25`

```python
SECRET_KEY: str = "your-secret-key-here-change-in-production"
```

**风险**:
- ❌ 硬编码默认值暴露在源代码中
- ❌ 如果直接用生产，JWT token 可被任意伪造
- ❌ 部署脚本未强制要求修改

**修复方案**:
```python
# config.py
import os

SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    None
)

def __init__(self):
    if not self.SECRET_KEY:
        raise ValueError(
            "SECRET_KEY must be set in environment variables. "
            "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
```

**优先级**: 🔴 立即修复 (部署前)

---

### 2. 调试模式配置 🔴 高风险

**问题位置**: `backend/app/core/config.py:14`

```python
DEBUG: bool = True
```

**风险**:
- ❌ 生产环境启用 DEBUG 会暴露敏感堆栈跟踪
- ❌ FastAPI 自动生成的 SQL 日志输出到控制台
- ❌ Swagger/Redoc API 文档在生产对外暴露（可遍历所有接口）

**修复方案**:
```bash
# .env 文件
DEBUG=false
DOCS_URL=null  # 生产环境关闭 API 文档
REDOC_URL=null
```

```python
# main.py
docs_url="/docs" if settings.DEBUG else None,
redoc_url="/redoc" if settings.DEBUG else None,
```

**优先级**: 🔴 立即修复

---

### 3. 文件上传安全性 🔴 高风险

**问题位置**: `backend/app/api/v1/endpoints/photos.py:upload_photo()`

**现状**:
```python
# ❌ 缺少文件类型校验
async def upload_photo(
    file: UploadFile = File(...),
    ...
):
    # 直接保存，未检查 MIME type
    await save_photo_file(file)
```

**风险**:
- ❌ 允许上传恶意文件 (exe, php, zip 等)
- ❌ 通过文件名注入构建路径遍历攻击
- ❌ 文件大小限制只有客户端检查，服务端未强制

**修复方案**:
```python
from fastapi import UploadFile, File
import magic  # 或 python-magic-bin

ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

async def upload_photo(
    file: UploadFile = File(...),
):
    # 1. 检查文件大小
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # 2. 检查真实 MIME type (不信任 Content-Type 头)
    file_type = magic.Magic(mime=True).from_buffer(contents)
    if file_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # 3. 验证文件签名 (magic number)
    if not _is_valid_image(contents):
        raise HTTPException(status_code=400, detail="File is not a valid image")
    
    await file.seek(0)  # 重置文件指针
    ...
```

**优先级**: 🔴 立即修复

---

### 4. CORS 配置过宽 🟡 中风险

**问题位置**: `backend/app/core/config.py:37-42`

```python
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000"
]
```

**风险**:
- ❌ 允许开发环境的所有端口
- ❌ 生产环境未配置域名白名单
- ❌ 允许跨域 Cookie 发送（auto_error=False）

**修复方案**:
```python
import os

# 分环境配置
if settings.DEBUG:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
else:
    ALLOWED_ORIGINS = [
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ]

# 只允许必要的凭证
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # 仅用于 JWT Bearer token
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 明确列出
    allow_headers=["Content-Type", "Authorization"],
)
```

**优先级**: 🟡 修复 (部署前)

---

### 5. 密码验证逻辑 ✅ 合理

**评估**: `backend/app/crud/user.py:93-105`

```python
async def authenticate_user(db, identifier, password):
    user = await get_user_by_email(db, identifier)
    if not user:
        user = await get_user_by_student_id(db, identifier)
    if not verify_password(password, user.hashed_password):
        return None
```

✅ 使用 bcrypt 哈希，支持邮箱/学号双重登录  
✅ 密码验证使用恒定时间算法（bcrypt 内置）  
⚠️ **建议**: 添加 rate limiting 防止暴力破解

---

### 6. API 权限检查 ✅ 合理

**评估**: `backend/app/core/deps.py:45-68`

✅ 三层权限模型：
- `get_current_user` - 仅需登录
- `get_current_admin_user` - 需要 admin 角色
- `get_optional_current_user` - 可选登录

✅ JWT token 使用 student_id 作为 subject  
✅ 权限检查贯穿 API 层

**改进建议**:
```python
# 添加审计日志
async def get_current_admin_user(...):
    if current_user.role != "admin":
        logger.warning(
            f"Unauthorized admin access: user={current_user.id}, "
            f"endpoint={request.url.path}"
        )
        raise HTTPException(...)
```

---

## ⚡ 性能分析

### 1. 数据库选择 🟡 中等

**现状**: SQLite + aiosqlite

**优点**:
- ✅ MVP 快速迭代理想
- ✅ 零配置，开发体验好
- ✅ 异步支持完善

**缺点** (生产环境):
- ❌ 单进程并发写入限制
- ❌ 无分布式支持
- ❌ 文件系统依赖，较大数据集性能下降

**建议时间表**:
```
现在 (MVP)         → SQLite ✓
100K+ 张照片      → PostgreSQL + AsyncPG
1M+ 张照片 + 分布式 → PostgreSQL Sharding
```

**迁移方案**:
```python
# requirements.txt 添加
asyncpg>=0.28.0
```

---

### 2. 缓存缺失 🟡 中风险

**问题**: 无 Redis/内存缓存，每次查询都走数据库

**高频查询场景** (缺乏缓存):
- 照片列表分页 (50+ QPS/10s = 每秒多次查询同一页)
- 用户权限检查 (每个请求都查 User 表)
- 系统配置查询 (get_system_config 每次都读库)

**修复方案**:
```python
# 使用 Pydantic 内置缓存或 functools
from functools import lru_cache
from datetime import datetime, timedelta

class CacheManager:
    _cache = {}
    
    @staticmethod
    async def get_cached(key: str, ttl: int, fetch_fn):
        """通用缓存函数"""
        if key in CacheManager._cache:
            value, expire_at = CacheManager._cache[key]
            if datetime.now() < expire_at:
                return value
        
        value = await fetch_fn()
        CacheManager._cache[key] = (value, datetime.now() + timedelta(seconds=ttl))
        return value

# 使用示例
async def get_photos_with_cache(params):
    cache_key = f"photos:{hash(str(params))}"
    return await CacheManager.get_cached(
        cache_key, 
        ttl=300,
        fetch_fn=lambda: photo_crud.get_photos(params)
    )
```

**优先级**: 🟡 MVP 后期优化

---

### 3. AI 服务调用 🟡 性能隐患

**问题位置**: `backend/app/services/ai_tagging.py`

**现状**:
```python
async def analyze_image(self, image_path: str):
    # 同步调用 Ollama HTTP API，等待响应
    result = await self._call_ollama_api(...)
```

**风险**:
- ❌ 网络 I/O 阻塞 (Ollama 模型推理可能 5-30 秒)
- ❌ 单个上传卡死整个服务
- ❌ 无超时控制或重试机制

**修复方案**:
```python
# 1. 改为后台任务
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_with_ai(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    photo = await save_photo(file)
    
    # 返回立即响应，后台处理 AI 分析
    background_tasks.add_task(
        analyze_and_update_photo,
        photo.id
    )
    return {"photo_id": photo.id, "status": "processing"}

# 2. 添加超时和重试
async def analyze_with_timeout(image_path: str):
    try:
        return await asyncio.wait_for(
            self._call_ollama_api(image_path),
            timeout=30
        )
    except asyncio.TimeoutError:
        logger.error(f"AI analysis timeout: {image_path}")
        return None  # 失败继续，不中断上传
```

**优先级**: 🟡 修复 (部署前)

---

## 🎨 代码质量

### 1. 错误处理不一致 🟡 中等

**问题示例**:

```python
# ❌ 生产环境这会导致堆栈追踪暴露
try:
    with Image.open(image_path) as img:
        return img.size
except Exception as e:
    # 直接 raise，不处理
    raise

# ❌ 调试代码留在里面
print(f"Error processing image: {e}")

# ✅ 推荐做法
logger.error(f"Image processing failed: {image_path}", exc_info=True)
raise HTTPException(status_code=400, detail="Invalid image")
```

**修复要点**:
- 用 logger 替代 print
- 向客户端返回通用错误信息，内部日志记录详情
- 为不同错误定义自定义异常类

---

### 2. 日志混乱 🟡 中等

**现状**: 混用 logger.debug, print, logger.info 无统一策略

**建议**:
```python
# config.py 统一配置日志
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default", "file"],
            "level": "INFO" if not DEBUG else "DEBUG",
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

---

### 3. 类型注解完整度 ✅ 良好

**评估**:
- ✅ 后端: Pydantic Schema + 函数类型注解完整
- ✅ 前端: TypeScript + 类型定义齐全
- ✅ 使用 type hints 支持 IDE 自动完成

**小改进**:
```python
# 返回值类型注解缺失
async def save_photo_file(upload_file: UploadFile) -> tuple[str, str, str, str]:
    # ✅ 很好，但可以用 TypedDict 让返回值意义更清晰
    
from typing import TypedDict

class PhotoFileInfo(TypedDict):
    uuid: str
    path: str
    filename: str
    extension: str

async def save_photo_file(upload_file: UploadFile) -> PhotoFileInfo:
    ...
```

---

### 4. 代码组织 ✅ 清晰

**评估**:
```
backend/
├── core/        # 配置、数据库、安全 ✅ 内聚
├── api/         # 路由器 ✅ 按功能模块
├── models/      # ORM 模型 ✅ 清晰
├── schemas/     # Pydantic Schema ✅ 请求/响应定义
├── crud/        # 数据库操作 ✅ 关注点分离
├── services/    # 业务逻辑 ✅ 可测试
├── utils/       # 工具函数 ✅ (目前为空，可以有所改进)
└── main.py      # 应用入口 ✅
```

**建议**: 补充 `utils/` 文件，提取公用函数 (路径验证、文件处理等)

---

## 🚀 运维与部署

### 1. 环境变量管理 🟡 中等

**问题**: 依赖环境变量，但部署文档不清晰

**建议**:
```bash
# 创建 .env.example 文件（纳入版本控制）
# backend/.env.example
SECRET_KEY=your-secret-key-change-this
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./prod.db
UPLOAD_DIR=/var/www/buct_media/uploads
MAX_UPLOAD_SIZE=20971520
OLLAMA_API_URL=http://localhost:11434
AI_ENABLED=true
AI_MODEL_NAME=llava
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=["https://yourdomain.com"]
```

**部署脚本改进**:
```bash
# deploy.sh
if [ ! -f "${APP_DIR}/backend/.env" ]; then
    cp "${APP_DIR}/deploy/.env.example" "${APP_DIR}/backend/.env"
    echo "⚠️  请编辑 .env 文件并设置 SECRET_KEY!"
    exit 1
fi
```

---

### 2. 数据库迁移 ✅ 有 Alembic

**评估**: 已集成 Alembic，但迁移历史很少

```bash
backend/alembic/versions/
├── f9663193e169_initial_schema.py  # 只有初始化
```

**建议**:
```bash
# 进行每次 schema 变更时生成迁移
alembic revision --autogenerate -m "add_user_is_active_field"
alembic upgrade head
```

---

### 3. 静态文件和上传管理 🟡 中等

**问题**:
- 上传文件存在本地文件系统
- 无分布式存储支持
- 缺少清理过期文件的机制

**现状结构**:
```
uploads/
├── originals/   # 原始文件
├── thumbnails/  # 缩略图
└── processed/   # (可能的处理后文件)
```

**Nginx 配置**:
```nginx
# ✅ 防止执行上传的脚本很好
location ~* \.(php|py|sh|pl)$ {
    deny all;
}

# ✅ 静态资源缓存设置良好
expires 30d;
add_header Cache-Control "public, immutable";
```

**改进建议** (中期):
```python
# 支持 S3 存储后端
import boto3

class S3StorageService:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = os.getenv('S3_BUCKET')
    
    async def upload(self, file_path: str):
        self.s3.upload_file(
            file_path,
            self.bucket,
            f"photos/{uuid4()}.jpg"
        )
```

---

## 🔄 前端代码审查

### 1. API 调用错误处理 ✅ 合理

**评估**: `frontend/src/api/index.ts`

```typescript
// ✅ 统一拦截器处理
request.interceptors.response.use(
    response => response.data,
    error => {
        // ✅ 401 自动清除 token 并重定向
        if (response.status === 401) {
            localStorage.removeItem('auth_token')
            window.location.href = '/login'
        }
        // ✅ 详细的状态码处理
        throw error
    }
)
```

**改进**:
```typescript
// 添加请求超时重试
const retryConfig = {
    retries: 3,
    timeout: 30000,
}

// 添加请求队列，防止并发重复请求
const requestQueue = new Map()

request.interceptors.request.use(config => {
    const key = `${config.method}:${config.url}`
    if (requestQueue.has(key)) {
        return requestQueue.get(key)  // 返回已存在的 Promise
    }
    
    const promise = Promise.resolve(config)
    requestQueue.set(key, promise)
    
    return promise
})
```

---

### 2. 状态管理 ✅ 清晰

**评估**: `frontend/src/stores/auth.ts`

✅ 使用 Pinia (官方推荐)  
✅ Token 持久化到 localStorage  
✅ 三层权限判断 (isAdmin, isAuditor, hasRole)

**改进**:
```typescript
// 添加权限刷新机制
export const useAuthStore = defineStore('auth', () => {
    // 定期检查 token 有效性
    async function initFromStorage() {
        const token = localStorage.getItem('auth_token')
        if (token) {
            try {
                await fetchCurrentUser()  // 验证 token
                // 添加定时器，在 token 过期前刷新
                setupTokenRefresh()
            } catch {
                logout()  // token 无效，清除
            }
        }
    }
    
    function setupTokenRefresh() {
        setInterval(() => {
            if (isAuthenticated.value) {
                // 调用刷新接口（需要后端支持）
                refreshToken()
            }
        }, 1000 * 60 * 15)  // 15 分钟刷新一次
    }
})
```

---

### 3. 用户输入验证 ✅ 基础

**评估**: `frontend/src/views/Login.vue`

```typescript
const loginRules: FormRules = {
    identifier: [
        { required: true, message: '学号或邮箱不能为空', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '密码不能为空', trigger: 'blur' },
        { min: 6, message: '密码至少 6 位', trigger: 'blur' }
    ]
}
```

✅ 基础验证存在  
🟡 **改进建议**:
```typescript
// 添加格式验证
const loginRules = {
    identifier: [
        { required: true, trigger: 'blur' },
        {
            pattern: /^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|\d{8,12})$/,
            message: '学号 (8-12 位) 或邮箱格式不正确',
            trigger: 'blur'
        }
    ]
}
```

---

### 4. 文件上传 🟡 中等

**位置**: `frontend/src/views/Upload.vue`

**现状**:
```typescript
// ❌ 客户端文件大小检查，可被绕过
if (file.size > 20 * 1024 * 1024) {
    message.error('文件过大')
    return
}
```

**改进**:
```typescript
// ✅ 服务端强制，客户端提前反馈
const MAX_FILE_SIZE = 20 * 1024 * 1024

async function handleUpload(file: File) {
    // 1. 客户端提前检查，改善 UX
    if (file.size > MAX_FILE_SIZE) {
        message.error('文件过大，请选择小于 20MB 的图片')
        return
    }
    
    // 2. 检查文件类型（不完全可信）
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        message.error('仅支持 JPEG、PNG、WebP 格式')
        return
    }
    
    // 3. 上传进度反馈
    try {
        await photoApi.upload(file, (progress) => {
            uploadProgress.value = Math.round(
                (progress.loaded / progress.total) * 100
            )
        })
    } catch (error) {
        if (error.response?.status === 413) {
            message.error('文件过大，服务器拒绝')
        } else {
            message.error('上传失败')
        }
    }
}
```

---

## 📊 数据库设计

### 1. 索引优化 🟡 中等

**现状**:
```python
# Photo 模型
id = Column(String(36), primary_key=True)
created_at = Column(DateTime, ..., index=True)
uploader_id = Column(..., ForeignKey(...))
```

**缺失的索引** (高频查询):
```python
class Photo(Base):
    __tablename__ = "photos"
    
    # ❌ 缺少复合索引
    # 常见查询: WHERE status='approved' ORDER BY created_at DESC
    
    # ✅ 应添加
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_uploader_created', 'uploader_id', 'created_at'),
        Index('idx_season_category', 'season', 'category'),
    )
```

---

### 2. 关系完整性 ✅ 良好

**评估**:
```python
# ✅ 级联删除配置合理
photos = relationship("Photo", cascade="all, delete-orphan")

# ✅ 外键约束正确
uploader_id = ForeignKey("users.id")
```

---

## 🐛 已知 BUG 和改进点

### 1. 路径错误 ✅ 已修复
- ❌ 前端调用 `/api/v1/login` (路由不存在)
- ✅ 修复为 `/api/v1/auth/login`

### 2. 环境变量配置混乱 🟡 需改进
- `frontend/.env` 指向 8001 端口
- `frontend/.env.development` 指向 8000 端口
- 需要统一注释或删除

**建议**:
```bash
# 检查并删除不用的 .env 文件
rm frontend/.env  # 只保留 .env.development 和 .env.production
```

### 3. 前后端端口配置 🟡 需审查

**nginx.conf** 中:
```nginx
server_name your-domain.com;  # ❌ 硬编码，需参数化
```

**部署脚本** 中:
```bash
DOMAIN="your-domain.com"  # ❌ 硬编码，应来自参数
```

---

## 📝 检查清单 - 部署前必须完成

- [ ] **安全**
  - [ ] 修改 SECRET_KEY，不用默认值
  - [ ] 设置 DEBUG=false
  - [ ] 添加文件上传类型校验
  - [ ] 配置 CORS 白名单（不用 localhost:*）
  - [ ] 设置数据库密码（如升级到 PostgreSQL）

- [ ] **性能**
  - [ ] 调整 AI 服务为背景任务
  - [ ] 添加 Ollama API 超时控制
  - [ ] 验证数据库索引

- [ ] **运维**
  - [ ] 生成并保存 SECRET_KEY
  - [ ] 配置生产环境 .env 文件
  - [ ] 创建 uploads 目录并设置权限
  - [ ] 初始化数据库
  - [ ] 配置 Nginx 域名和 SSL
  - [ ] 代码审查部署脚本

- [ ] **前端**
  - [ ] 验证 API 基础 URL 配置
  - [ ] 构建生产版本 (npm run build)
  - [ ] 测试 CORS 请求

- [ ] **监控与日志**
  - [ ] 配置日志文件输出
  - [ ] 设置错误告警 (Sentry/DataDog)
  - [ ] 配置备份策略

---

## 📈 中期改进方案（3-6 个月）

### Phase 1: 稳定性强化
1. 升级到 PostgreSQL
2. 添加 Redis 缓存层
3. 实现 API 速率限制 (rate limiting)
4. 添加审计日志

### Phase 2: 可扩展性
1. 分离 AI 处理为微服务
2. 支持分布式文件存储 (S3)
3. 消息队列处理异步任务 (Celery/RQ)

### Phase 3: 观测性
1. 分布式链路追踪 (Jaeger/Zipkin)
2. 应用性能监控 (APM)
3. 日志汇聚 (ELK Stack)

---

## 📚 推荐资源

| 话题 | 推荐 |
|------|------|
| FastAPI 安全最佳实践 | https://fastapi.tiangolo.com/advanced/security/ |
| OWASP Top 10 | https://owasp.org/www-project-top-ten/ |
| SQLAlchemy 性能 | https://docs.sqlalchemy.org/en/20/faq/performance.html |
| Vue 3 安全 | https://v3.vuejs.org/guide/security.html |

---

## 总结评分

| 维度 | 评分 | 备注 |
|------|------|------|
| 代码架构 | 8/10 | 清晰合理，关注点分离好 |
| 功能完整 | 8/10 | MVP 阶段完整，生产还需加强 |
| 安全性 | 5/10 | 🔴 需要立即修复的问题 |
| 性能基础 | 7/10 | 异步设计好，缓存缺失 |
| 可运维性 | 6/10 | 脚本完整，配置管理可改进 |
| **总体** | **6.8/10** | 🟡 **需要修复关键问题后才能生产** |

---

**制作时间**: 2026-03-02  
**下次审查**: 修复关键问题后，建议 2 周内再审查一次
