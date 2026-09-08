"""FastAPI entrypoint for the Safe Pedestrian Route project.

This first foundation intentionally exposes only a health check. Future route
recommendation capabilities can be added without coupling the API to the UI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Safe Pedestrian Route API",
    version="0.1.0",
    description="Backend foundation for safer pedestrian route recommendations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a small response so the frontend can confirm the API is running."""

    return {"status": "ok", "service": "safe-walk-ai-backend"}