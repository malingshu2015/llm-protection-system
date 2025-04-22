"""Main entry point for the Local LLM Protection System."""

import asyncio
import signal
import sys
from typing import Dict, Set

import os
import uvicorn
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from src.config import settings
from src.logger import logger
from src.web.api import router as api_router
from src.web.rules_api import router as rules_router
from src.web.metrics_api import router as metrics_router
from src.web.health_api import router as health_router
from src.web.model_rules_api import router as model_rules_router
from src.web.events_api import router as events_router


app = FastAPI(
    title=settings.app_name,
    description="A protection system for local large language models",
    version="0.1.0",
    debug=True,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Register API routes
app.include_router(api_router)
app.include_router(rules_router)
app.include_router(metrics_router)
app.include_router(health_router)
app.include_router(model_rules_router)
app.include_router(events_router)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    # 先挂载静态文件，然后再注册路由
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# 添加 favicon.ico 路由
@app.get("/favicon.ico")
async def favicon():
    # 返回空的 favicon
    return Response(content=b"", media_type="image/x-icon")

# Add root route - 直接返回简单的 HTML
@app.get("/")
async def root():
    return Response(
        content="<html><body><h1>本地大模型防护系统</h1><p>Welcome to the Local LLM Protection System.</p><p><a href='/static/index.html'>Go to Chat Demo</a></p></body></html>",
        media_type="text/html"
    )

# Store running tasks
running_tasks: Set[asyncio.Task] = set()


async def startup_event() -> None:
    """Initialize services on application startup."""
    logger.info("Starting Local LLM Protection System")

    # 创建必要的目录
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.data_dir, "security_events"), exist_ok=True)
    os.makedirs(settings.rules.rules_path, exist_ok=True)

    # Start background tasks
    task = asyncio.create_task(background_tasks())
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)


async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    logger.info("Shutting down Local LLM Protection System")

    # Cancel all running tasks
    for task in running_tasks:
        task.cancel()

    # Wait for all tasks to complete
    if running_tasks:
        await asyncio.gather(*running_tasks, return_exceptions=True)


async def background_tasks() -> None:
    """Run background tasks."""
    try:
        while True:
            # Perform periodic tasks
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Background tasks cancelled")
    except Exception as e:
        logger.exception(f"Error in background tasks: {e}")


# Register startup and shutdown events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


def handle_signals() -> None:
    """Set up signal handlers."""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main() -> None:
    """Run the application."""
    handle_signals()

    # Start the web server
    uvicorn.run(
        "src.main:app",
        host=settings.web.host,
        port=settings.web.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
