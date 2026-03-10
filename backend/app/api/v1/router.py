"""
API v1 router aggregation

API v1 版本路由聚合，注册所有端点模块。
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, photos, tags, import_photos, stats, taxonomy, notifications, profile, favorites
from app.api.v1.endpoints import admin_users, admin_config, admin_permissions, admin_audit

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(photos.router, prefix="/photos", tags=["Photos"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
api_router.include_router(taxonomy.router, prefix="/taxonomy", tags=["Taxonomy"])
api_router.include_router(import_photos.router, prefix="/photos", tags=["Import"])
api_router.include_router(stats.router, prefix="/stats", tags=["Statistics"])
api_router.include_router(notifications.router, prefix="/user", tags=["Notifications"])
api_router.include_router(profile.router, prefix="/user", tags=["Profile"])
api_router.include_router(favorites.router, prefix="/photos", tags=["Favorites"])

# Admin endpoint routers (权限管理接口)
api_router.include_router(admin_users.router, prefix="/admin", tags=["用户管理"])
api_router.include_router(admin_config.router, prefix="/admin", tags=["系统设置"])
api_router.include_router(admin_permissions.router, prefix="/admin", tags=["授权管理"])
api_router.include_router(admin_audit.router, prefix="/admin", tags=["审计日志"])
