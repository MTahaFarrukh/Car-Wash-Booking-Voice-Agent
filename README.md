# Sparkle AI Receptionist (carwash-ai)

AI-powered car wash receptionist and booking platform — a monorepo with a Next.js frontend and FastAPI backend backed by PostgreSQL (Supabase).

**Phase 1** delivers the project foundation: health endpoints, SQLAlchemy models, Alembic config, and a minimal landing page.

**Phase 2** adds Alembic migrations, database indexes, and idempotent development seed data.

Booking logic, REST APIs, auth, and voice integration arrive in later phases.

## Project structure

```
carwash-ai/
├── frontend/          # Next.js App Router + TypeScript + Tailwind + shadcn/ui
├── backend/
│   ├── app/           # FastAPI application
│   ├── alembic/       # Database migrations
│   └── scripts/       # Development seed scripts
├── .env.example       # Shared environment template
└── README.md
```

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** (local install or Supabase connection string)

## Quick start

### 1. Environment

Copy the root environment template and fill in your values (especially `DATABASE_URL`):

```powershell
copy .env.example .env
```

For the frontend:

```powershell
copy frontend\.env.local.example frontend\.env.local
```

### 2. Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database migrations (Phase 2)

Ensure PostgreSQL is running and `DATABASE_URL` in the root `.env` is valid (local Postgres or Supabase direct connection string).

```powershell
cd backend
venv\Scripts\activate
alembic upgrade head
```

Verify migration:

```powershell
alembic downgrade -1
alembic upgrade head
```

### 4. Seed development data (Phase 2)

```powershell
python -m scripts.seed
```

The seed script is idempotent — it skips if data already exists. To inspect counts after seeding:

```powershell
python -m scripts.seed --verify
```

### 5. Run backend

```powershell
uvicorn app.main:app --reload --port 8000
```

Verify:

- `GET http://localhost:8000/health` → `{ "status": "ok" }`
- `GET http://localhost:8000/health/db` → `{ "database": "connected" }` (requires valid `DATABASE_URL`)
- API docs at `http://localhost:8000/docs`

### 6. Frontend

In a new terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` — the landing page shows live backend and database health status.

Production build check:

```powershell
npm run build
```

## Phase 2 scope

| Included | Deferred |
|----------|----------|
| Initial Alembic migration (`f8a2b1c3d4e5`) | Booking service and REST routers (Phases 3–4) |
| Indexes on booking status, dates, customer phone, call start time | Dashboard pages (Phase 5) |
| Idempotent seed script (`python -m scripts.seed`) | Supabase Auth (Phase 6) |
| Sample business data (Sparkle Car Wash) | AI tools and Uplift integration (Phases 7–8) |

## Phase 1 scope

| Included | Deferred |
|----------|----------|
| Monorepo layout and env scaffolding | Migrations and seed data (Phase 2) |
| FastAPI `/health` and `/health/db` | Booking service and REST routers (Phases 3–4) |
| SQLAlchemy models (User, Customer, Vehicle, Service, Booking, Availability, CallLog) | Dashboard pages (Phase 5) |
| Alembic config (no migrations yet) | Supabase Auth (Phase 6) |
| Next.js landing page with health UI | AI tools and Uplift integration (Phases 7–8) |

## Environment variables

| Variable | Used by | Phase |
|----------|---------|-------|
| `DATABASE_URL` | Backend | 1 |
| `CORS_ORIGINS` | Backend | 1 |
| `NEXT_PUBLIC_API_URL` | Frontend | 1 |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Backend | 6 |
| `UPLIFT_API_KEY`, `UPLIFT_AGENT_ID` | Backend | 8 |

See [`.env.example`](.env.example) for the full list.

## License

Private project — not for public distribution.
