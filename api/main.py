"""
FastAPI application exposing the equipment booking agent over HTTP.

Endpoints:
- GET  /          → redirect to /ui/index.html
- GET  /health    → simple health check
- POST /chat      → chat interface with per-session memory
- Static files at /ui served from the ui/ directory
"""

from __future__ import annotations

import uuid
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from agent.agent import agent


logger = logging.getLogger(__name__)


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str
    session_id: Optional[str] = None  # auto-generated if not supplied


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    response: str
    session_id: str


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="EquiBot — College Equipment Booking Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the single-file web UI as static files at /ui.
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect the bare root URL to the web UI."""

    return RedirectResponse(url="/ui/index.html")


@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""

    return {"status": "ok", "message": "EquiBot is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint that proxies messages to the booking agent.

    If no session_id is provided a new UUID is generated so the client
    can include it in subsequent requests to maintain context.
    """

    session_id = request.session_id or str(uuid.uuid4())

    try:
        reply = agent.chat(session_id, request.message)
        return ChatResponse(response=reply, session_id=session_id)
    except Exception as exc:
        logger.exception("Unhandled error in /chat endpoint")
        return ChatResponse(
            response=f"⚠️ An error occurred while handling your request: {exc}",
            session_id=session_id,
        )
