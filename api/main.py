"""
Secure Media Processor - Serverless API
FastAPI application with AWS Lambda handler via Mangum
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.config import settings
from app.routers import auth, files, licenses, users, health

# Initialize FastAPI app
app = FastAPI(
    title="Secure Media Processor API",
    description="API for secure media processing with encryption and cloud storage",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "prod" else None,
    redoc_url="/redoc" if settings.environment != "prod" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(licenses.router, prefix="/api/licenses", tags=["Licenses"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Secure Media Processor API",
        "version": "1.0.0",
        "status": "running"
    }


# Lambda handler
handler = Mangum(app, lifespan="off")
