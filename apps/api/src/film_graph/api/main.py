"""Installed import path for the M00 FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

SERVICE_NAME = "film-production-graph-api"
SERVICE_VERSION = "0.1.0"


def _health_payload() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


def create_app() -> FastAPI:
    application = FastAPI(
        title="Film Production Graph API",
        version=SERVICE_VERSION,
        description="M00 deterministic foundation API; no provider calls are made.",
    )

    @application.get("/", tags=["diagnostics"])
    def root() -> dict[str, str]:
        return _health_payload()

    @application.get("/health", tags=["diagnostics"])
    @application.get("/api/health", tags=["diagnostics"])
    def health() -> dict[str, str]:
        return _health_payload()

    return application


app = create_app()
