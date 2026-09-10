from fastapi import APIRouter

from app.features.health.routes import router as health_router

feature_router = APIRouter()

feature_router.include_router(health_router)
