from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"success": True, "data": {"status": "ok", "env": settings.ENV}}
