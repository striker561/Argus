from fastapi import APIRouter

from app.features.health.schema import StatusData

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> StatusData:
    return StatusData(status="ok")
