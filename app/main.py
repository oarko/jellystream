"""Main application entry point."""

import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.api import router as api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="JellyStream",
    description="Media streaming integration for Jellyfin",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/web/templates")

# Include routers
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting JellyStream application...")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    await init_db()
    logger.info("Database initialized successfully")

    from app.services.scheduler import start_scheduler
    start_scheduler()

    logger.info(f"JellyStream started on {settings.HOST}:{settings.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown."""
    logger.info("Shutting down JellyStream...")
    from app.services.scheduler import stop_scheduler
    stop_scheduler()
    logger.info("JellyStream shutdown complete")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serves web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {"message": "JellyStream API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint - returns empty response to suppress warnings."""
    return Response(status_code=204)
