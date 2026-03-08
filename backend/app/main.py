"""FastAPI 应用主入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os
from app.core.config import get_settings
from app.api.v1.router import api_router

settings = get_settings()

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

openapi_tags = [
    {
        "name": "Authentication",
        "description": "登录、注册与当前用户信息。`/auth/login` 使用 JSON 请求体，`/auth/token` 用于 OpenAPI/OAuth2 password flow。",
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

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
