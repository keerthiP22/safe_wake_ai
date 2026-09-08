# Safe Pedestrian Route Recommendation

Beginner-friendly foundation for an urban pedestrian safety route recommendation project.

## Run & Operate

- `pnpm --filter @workspace/safe-pedestrian-route run dev` — run the React frontend
- `uvicorn backend.main:app --reload --port 8000` — run the FastAPI backend locally
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm --filter @workspace/safe-pedestrian-route run build` — build the frontend
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Python + FastAPI
- Frontend: React + TypeScript + Vite
- API codegen: Orval (from OpenAPI spec)

## Where things live

- `artifacts/safe-pedestrian-route/` — React + TypeScript frontend
- `backend/` — Python + FastAPI backend
- `lib/api-spec/openapi.yaml` — source of truth for the current API contract
- `lib/api-client-react/` — generated React Query client

## Architecture decisions

- The first API surface is intentionally limited to `GET /api/healthz`; product capabilities will be added incrementally.
- Frontend and backend live in separate top-level directories so the boundary stays clear for beginner contributors.

## Product

The foundation presents the project purpose and confirms whether the FastAPI backend is available. Mapping, routing, AI/ML, authentication, and external data sources are intentionally not included yet.

## User preferences

- Keep the first iterations simple and beginner-friendly.
- Do not add Mapbox, OpenStreetMap, Overpass, AI/ML, Supabase, authentication, routing, or fake/demo data unless explicitly requested later.

## Gotchas

- Keep `lib/api-spec/openapi.yaml` synchronized with backend endpoints and regenerate the typed client after contract changes.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
