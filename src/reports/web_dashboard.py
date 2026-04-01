"""FastAPI web dashboard with HTMX and WebSocket chat."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from ..config import AppConfig

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app(config: AppConfig) -> FastAPI:
    """Create and configure the FastAPI dashboard application.

    Args:
        config: Application configuration.

    Returns:
        Configured FastAPI app.
    """
    app = FastAPI(title="Copilot Pulse Dashboard", version="0.1.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Store config and orchestrator reference on app state
    app.state.config = config
    app.state.orchestrator = None  # Set externally before startup

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Main dashboard page with KPI cards and charts."""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Copilot Pulse Dashboard",
                "enterprise": config.github_enterprise,
                "org": config.github_org,
            },
        )

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page(request: Request):
        """Chat interface page."""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Copilot Pulse Chat",
                "active_tab": "chat",
                "enterprise": config.github_enterprise,
                "org": config.github_org,
            },
        )

    @app.get("/api/metrics")
    async def api_metrics():
        """API endpoint for fetching metrics data (used by HTMX)."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}

        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
            return result
        except Exception as e:
            logger.error("API metrics error: %s", e)
            return {"error": str(e)}

    @app.get("/api/seat-info")
    async def api_seat_info():
        """API endpoint for seat information."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}

        try:
            result = await orch._tool_seat_info({"org": config.github_org})
            return result
        except Exception as e:
            logger.error("API seat info error: %s", e)
            return {"error": str(e)}

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        """WebSocket endpoint for real-time chat with the agent."""
        await websocket.accept()
        orch = app.state.orchestrator

        if not orch:
            await websocket.send_json({"type": "error", "message": "Agent not initialized"})
            await websocket.close()
            return

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                question = message.get("question", "")

                if not question:
                    continue

                await websocket.send_json({"type": "status", "message": "Analizzo..."})

                try:
                    response = await orch.ask(question)
                    await websocket.send_json({
                        "type": "response",
                        "message": response,
                    })
                except Exception as e:
                    logger.error("Chat error: %s", e)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Errore: {e}",
                    })

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")

    return app
