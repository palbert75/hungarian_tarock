"""Main entry point for Hungarian Tarokk server."""

import uvicorn
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import socketio
import time

from networking.server import sio
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

# Create FastAPI app
fastapi_app = FastAPI(
    title="Hungarian Tarokk Server",
    description="WebSocket server for Hungarian Tarokk card game",
    version="1.0.0",
    debug=settings.debug
)

# Add request logging middleware
@fastapi_app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    print(f"\n>>> Incoming HTTP Request")
    print(f"    Method: {request.method}")
    print(f"    URL: {request.url}")
    print(f"    Path: {request.url.path}")
    print(f"    Headers: {dict(request.headers)}")

    response = await call_next(request)

    duration = time.time() - start_time
    print(f"<<< Response Status: {response.status_code} (took {duration:.3f}s)\n")

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
    print("\n" + "="*60)
    print("    HUNGARIAN TAROKK SERVER STARTING")
    print("="*60)
    print(f"Server URL: http://{settings.host}:{settings.port}")
    print(f"Socket.IO endpoint: http://{settings.host}:{settings.port}/socket.io/")
    print(f"Debug mode: {settings.debug}")
    print(f"CORS origins: {settings.cors_origins}")
    print("="*60 + "\n")

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
