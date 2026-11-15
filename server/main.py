"""Main entry point for Hungarian Tarokk server."""

import logging

import uvicorn
import structlog
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import hmac

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import socketio
import time

from networking.server import sio, init_persistence, shutdown_persistence, announce_restart, stats
from config import settings

# The server's own log lines go through the standard logging; without a
# handler nothing below a warning would ever be printed.
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")

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
    logger.info("server_lifecycle_starting", timestamp=datetime.now().isoformat())

    logger.info("initializing_persistence_system")
    persistence_result = await init_persistence()
    if persistence_result:
        logger.info("persistence_system_initialized_successfully")
    else:
        logger.warning("persistence_system_initialization_failed_continuing_without_persistence")

    logger.info("server_lifecycle_started", timestamp=datetime.now().isoformat())

    yield

    # Shutdown
    logger.info("server_lifecycle_shutting_down", timestamp=datetime.now().isoformat())
    await shutdown_persistence()
    logger.info("server_lifecycle_shutdown_complete", timestamp=datetime.now().isoformat())


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


@fastapi_app.get("/stats")
async def played_hands(request: Request, days: int = 30):
    """Played hands per day. Needs the header `Authorization: Bearer <STATS_TOKEN>`."""
    token = settings.stats_token
    given = request.headers.get("authorization", "")
    if not token:
        raise HTTPException(status_code=404)
    if not hmac.compare_digest(given.encode(), f"Bearer {token}".encode()):
        raise HTTPException(status_code=401)
    return stats(days)


# Wrap FastAPI app with Socket.IO
# Socket.IO handles /socket.io/* paths, FastAPI handles the rest
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


class GracefulServer(uvicorn.Server):
    """Tells the players and saves every table before the connections are closed."""

    async def shutdown(self, sockets=None):
        await announce_restart()
        await super().shutdown(sockets)


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

    if settings.debug:
        # Development: restart on every code change, print every frame
        uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True, log_level="debug")
        return

    config = uvicorn.Config(app, host=settings.host, port=settings.port, log_level="info", access_log=False)
    GracefulServer(config).run()


if __name__ == "__main__":
    main()
