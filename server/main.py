"""Main entry point for Hungarian Tarokk server."""

import uvicorn
import structlog
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import socketio
import time

from networking.server import sio, init_persistence, shutdown_persistence
from config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    # Startup
    logger.info("server_lifecycle_starting")
    await init_persistence()
    logger.info("server_lifecycle_started")

    yield

    # Shutdown
    logger.info("server_lifecycle_shutting_down")
    await shutdown_persistence()
    logger.info("server_lifecycle_shutdown_complete")


# Create FastAPI app
fastapi_app = FastAPI(
    title="Hungarian Tarokk Server",
    description="WebSocket server for Hungarian Tarokk card game",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# Add request logging middleware
@fastapi_app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.debug("incoming_http_request",
                 method=request.method,
                 url=str(request.url),
                 path=request.url.path,
                 headers=dict(request.headers))

    response = await call_next(request)

    duration = time.time() - start_time
    logger.debug("http_response",
                 status_code=response.status_code,
                 duration_seconds=duration)

    return response

# Add CORS middleware to FastAPI app
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Hungarian Tarokk Server",
        "version": "1.0.0",
        "status": "running"
    }


@fastapi_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Wrap FastAPI app with Socket.IO
# Socket.IO handles /socket.io/* paths, FastAPI handles the rest
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


def main():
    """Run the server."""
    logger.info("server_starting",
                host=settings.host,
                port=settings.port,
                server_url=f"http://{settings.host}:{settings.port}",
                socketio_endpoint=f"http://{settings.host}:{settings.port}/socket.io/",
                debug_mode=settings.debug,
                cors_origins=settings.cors_origins)

    logger.info(
        "starting_server",
        host=settings.host,
        port=settings.port,
        debug=settings.debug
    )

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug"  # Force debug level for more output
    )


if __name__ == "__main__":
    main()
