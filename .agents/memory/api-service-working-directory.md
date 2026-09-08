---
name: Python API workflow working directory
description: Why the managed API workflow changes directory before starting a top-level FastAPI package.
---

Managed API artifact services start with the artifact directory as their working directory. A Python package kept at the repository root is not importable until the workflow changes to the repository root first.

**Why:** The FastAPI backend is intentionally separate from the frontend and from the generated API client, so it lives in a top-level `backend/` package rather than inside the API artifact directory.

**How to apply:** When adding a top-level Python backend to a managed API service, launch it from the repository root (for example, with `cd ../.. && uv run uvicorn backend.main:app ...` from `artifacts/api-server`).