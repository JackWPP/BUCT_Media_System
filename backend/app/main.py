"""
FastAPI 应用主入口。

包含安全启动校验、全局异常处理、请求日志中间件等。
"""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from app.core.config import get_settings, DEFAULT_SECRET_KEY
from app.api.v1.router import api_router

# ────────────────────────────────────────────────────────────
# 日志配置
# ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("buct_media")

settings = get_settings()

# ────────────────────────────────────────────────────────────
# SECRET_KEY 启动校验（P0 安全：防止生产环境使用默认密钥）
# ────────────────────────────────────────────────────────────
if not settings.DEBUG and settings.SECRET_KEY == DEFAULT_SECRET_KEY:
    raise RuntimeError(
        "🚨 安全错误：生产环境中 SECRET_KEY 不能使用默认值！"
        "请在 .env 文件中设置一个强随机密钥，例如：\n"
        "  SECRET_KEY=$(python -c \"import secrets; print(secrets.token_urlsafe(64))\")"
    )

if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
    logger.warning(
        "⚠️  SECRET_KEY 使用默认值，仅适用于本地开发。"
        "部署前请务必在 .env 中配置强随机密钥。"
    )

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

openapi_tags = [
    {
        "name": "Authentication",
        "description": "登录、注册、Token 刷新与当前用户信息。`/auth/login` 使用 JSON 请求体，`/auth/token` 用于 OpenAPI/OAuth2 password flow。",
    },
    {
        "name": "Photos",
        "description": "照片上传、查询、审核、下载、标签维护与个人投稿管理。",
    },
    {
        "name": "Tags",
        "description": "标签查询与管理。",
    },
    {
        "name": "Taxonomy",
        "description": "受控分类体系（facet / node）查询与审核端维护接口。",
    },
    {
        "name": "Import",
        "description": "管理员批量导入照片与导入路径校验。",
    },
    {
        "name": "Statistics",
        "description": "浏览量统计与审核后台仪表盘数据。",
    },
    {
        "name": "用户管理",
        "description": "管理员用户列表、创建、更新、删除与角色变更。",
    },
    {
        "name": "系统设置",
        "description": "系统级配置，当前主要包括人像照片可见性策略。",
    },
    {
        "name": "授权管理",
        "description": "管理员按学号授予、查询、校验和撤销资源访问权限。",
    },
]


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    description=(
        "北京化工大学媒体资源管理系统后端接口。\n\n"
        "认证方式：大多数受保护接口使用 `Authorization: Bearer <token>`。\n"
        "前端常用登录接口为 `POST /api/v1/auth/login`，"
        "OpenAPI 工具链兼容登录接口为 `POST /api/v1/auth/token`。"
    ),
    openapi_tags=openapi_tags,
)


# ────────────────────────────────────────────────────────────
# 全局异常处理器（P0 安全：生产环境隐藏堆栈信息）
# ────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    捕获所有未处理的异常，防止堆栈信息泄露给客户端。
    """
    logger.error(
        "未处理的异常 [%s %s]: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    if settings.DEBUG:
        # 开发环境返回详细信息便于调试
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "code": "INTERNAL_ERROR"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试", "code": "INTERNAL_ERROR"},
    )


# ────────────────────────────────────────────────────────────
# 请求日志中间件
# ────────────────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个请求的方法、路径、状态码和耗时。"""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # 跳过健康检查等高频端点的日志
    if request.url.path not in ("/health", "/docs", "/redoc", "/openapi.json"):
        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

    return response


# ────────────────────────────────────────────────────────────
# CORS 配置（P0：收紧 methods 和 headers）
# ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
)

# ────────────────────────────────────────────────────────────
# 限流配置（P0：防止暴力破解和垃圾注册）
# ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


def custom_openapi():
    """Customize OpenAPI schema for import tools such as ApiFox."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema["servers"] = [
        {"url": "http://localhost:8000", "description": "本地开发环境"},
        {"url": "/", "description": "相对路径，适合反向代理或 ApiFox 自定义环境"},
    ]
    schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["description"] = (
        "使用 `POST /api/v1/auth/token` 获取 Bearer Token，"
        "或通过 `POST /api/v1/auth/login` 获取前端登录响应。"
    )
    schema["externalDocs"] = {
        "description": "项目部署与使用说明",
        "url": "/README.md",
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
