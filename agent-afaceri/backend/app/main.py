"""Agent Afaceri & Juridic AI — aplicație FastAPI.

Expune skill-uri de avocat (juridic) și de business și un chat contextual.
Provider AI: Anthropic Claude (fallback offline „mock" fără cheie).
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import auth, chat, documents, skills


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Agent Afaceri & Juridic AI",
    description="Asistent AI informativ pentru afaceri și juridic (România).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(documents.export_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "provider": settings.ai_provider}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "Agent Afaceri & Juridic AI",
        "docs": "/docs",
        "skills": "/skills",
        "chat": "/chat",
    }


# Pornire pe $PORT (util pentru platforme de hosting).
def _port() -> int:
    return int(os.getenv("PORT", "8000"))
