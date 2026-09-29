"""
ReliefChain AI - Modular Application Server.
Hosts emergency operations, explainable AI allocation, and foundational architecture
for the Digital Asset Verification & Disaster Compensation Module.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError, HTTPException
from .core.config import PROJECT_DIR, STORAGE_DIR, API_V1_PREFIX, PORT
from .core.database import check_db_health
from .core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from .schemas.common import HealthResponse
from .utils.helpers import get_current_utc_iso
from .api.v1.router import api_v1_router
try:
    from database import init_db
except (ImportError, ValueError):
    from ..database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized and uploads directory exists
    init_db()
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield

def create_application() -> FastAPI:
    """Application factory for ReliefChain AI."""
    app = FastAPI(
        title="ReliefChain AI API",
        version="1.0.0",
        description="Human-supervised AI platform for disaster-relief allocation & civic resilience",
        lifespan=lifespan
    )

    # Global CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Static file storage mount
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/api/storage/uploads", StaticFiles(directory=str(STORAGE_DIR)), name="uploads")

    frontend_dist = PROJECT_DIR / "frontend" / "dist"
    frontend_assets = frontend_dist / "assets"
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")

    # Direct Health / UI Entrypoints
    @app.get("/", summary="System Overview / Web Portal")
    def root(request: Request):
        accept = request.headers.get("accept", "")
        index_file = frontend_dist / "index.html"
        if index_file.exists() and not ("application/json" in accept and "text/html" not in accept):
            return FileResponse(str(index_file), media_type="text/html")
        return {
            "system": "ReliefChain AI",
            "tagline": "AI decides faster. Humans stay in control. Every critical decision is verifiable.",
            "status": "OPERATIONAL",
            "version": "1.0.0",
            "docs_url": "/docs",
            "health_url": "/health"
        }

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 404 and "text/html" in request.headers.get("accept", ""):
            path = request.url.path
            if not (path.startswith("/api") or path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/health")):
                index_path = frontend_dist / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path), media_type="text/html")
        return response

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Root Health Check",
        tags=["Health"]
    )
    def root_health() -> HealthResponse:
        """Root health check returning verified diagnostic status."""
        db_ok = check_db_health()
        storage_ok = STORAGE_DIR.exists()
        return HealthResponse(
            status="HEALTHY" if (db_ok and storage_ok) else "DEGRADED",
            database="CONNECTED" if db_ok else "DISCONNECTED",
            storage="ACCESSIBLE" if storage_ok else "UNAVAILABLE",
            version="1.0.0",
            timestamp=get_current_utc_iso()
        )

    # Backward compatibility /api/health endpoint
    @app.get("/api/health", response_model=HealthResponse, tags=["Health"])
    def api_health() -> HealthResponse:
        return root_health()

    # Mount versioned API routes (/api/v1/...)
    app.include_router(api_v1_router, prefix=API_V1_PREFIX)

    # Also mount under /api/... for backward compatibility with existing frontend calls
    app.include_router(api_v1_router, prefix="/api")

    # Mount directly at root (/assets, /claims, etc.) for direct API usage
    app.include_router(api_v1_router)

    return app

app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
