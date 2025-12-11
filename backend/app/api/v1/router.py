"""
API v1 router aggregation
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, photos

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(photos.router, prefix="/photos", tags=["Photos"])
