from fastapi import APIRouter
from app.models.response import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment=settings.app_env,
    )