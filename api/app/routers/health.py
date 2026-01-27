"""Health check endpoints"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "secure-media-processor-api"}


@router.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}
