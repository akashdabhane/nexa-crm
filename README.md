# NexaCRM

A full-stack CRM for small sales teams — contacts, companies, leads, deals, a Kanban sales pipeline,
activities, tasks, notes, notifications, reports and an audit log. Inspired by the core of HubSpot,
deliberately kept simple enough to understand end to end.

**Stack:** Next.js 16 · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query · FastAPI · SQLAlchemy 2 ·
Alembic · PostgreSQL · Supabase Auth · Docker Compose

---

## Features

| Area | What you can do |
|---|---|
| **Dashboard** | KPI tiles (contacts, companies, leads, active/won/lost deals, pipeline & weighted value, win rate, lead conversion), pipeline-by-stage and monthly revenue charts, recent activity, your upcoming tasks, lead sources |
| **Contacts** | CRUD, search (name/email/phone/title), filter by status/tag/owner, sort, paginate, tags, company link, activity timeline, deals, tasks, notes |
| **Companies** | CRUD, industry/owner filters, contact & deal counts, open pipeline value, company-wide timeline (includes its contacts' activity) |
| **Leads** | CRUD, status & source tracking, 0–100 lead score, **one-click conversion → Contact + Company + Deal** (matches an existing company by name, carries the lead's history over) |
| **Deals** | CRUD, list view with filters, clickable stage path, probability & weighted value, won/lost tracking |
| **Pipeline** | **Kanban board** with drag-and-drop between stages (optimistic updates) plus a "Move to" menu for touch devices |
| **Activities** | Log calls, meetings and emails against contacts, companies, leads and deals; chronological feed with type/owner/date filters |
| **Tasks** | Due dates, priorities, statuses, assignees, links to records; My tasks / Team, Open / Overdue / Completed views |
| **Notes** | On any contact, company, lead or deal; editable by the author |
| **Reports** | Lead conversion, sales pipeline, revenue by month, won vs lost, sales-rep performance, lead source performance — all with date filtering |
| **Notifications** | In-app: lead/deal/task assigned to you, task due, deal won/lost. Bell with unread count |
| **Audit log** | Who created, changed (field-level diff), converted, moved or deleted what, and when |
| **Auth & roles** | Supabase sign-up, login, email verification, password reset. Roles: Admin, Manager, Sales Rep |

### Roles

| | Admin | Manager | Sales Rep |
|---|:-:|:-:|:-:|
| View all records | ✅ | ✅ | ✅ |
| Create records | ✅ | ✅ | ✅ (owned by themselves) |
| Edit records | any | any | only their own |
| Reassign owner, delete records | ✅ | ✅ | ❌ (can delete their own activities, notes and tasks) |
| Rep performance report, audit log | ✅ | ✅ | ❌ |
| Manage users/roles & pipeline stages | ✅ | ❌ | ❌ |

The first account to sign in while no Admin exists becomes **Admin**; everyone else starts as Sales Rep.

---

## Architecture

```
 Browser ──(login, signup, reset)──▶ Supabase Auth ──▶ issues JWT
    │
    │  REST + Authorization: Bearer <JWT>
    ▼
 Next.js (App Router) ──Axios──▶ FastAPI ──SQLAlchemy──▶ PostgreSQL
  - proxy.ts refreshes the        - verifies the JWT (JWKS or HS256)
    session, guards routes        - loads/creates the user's profile + role
  - TanStack Query cache          - routes → services → models
                                  - audit log + notifications in the same transaction
```

- **Supabase is only the identity provider.** All CRM data lives in our PostgreSQL, owned by SQLAlchemy/Alembic.
  FastAPI never sees passwords; it verifies Supabase-signed tokens and keeps an app-side `profiles` table for roles.
- **Synchronous SQLAlchemy** — simple to read and debug; FastAPI runs sync endpoints in a thread pool.
- **No background workers.** Task-due notifications are created lazily when a user loads notifications; the bell polls every 60s.
- **Server-side search, filtering, sorting and pagination** for every list; sort columns are whitelisted.

More detail (schema, ER diagram, design decisions): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Project structure

```
nexa-crm/
├── docker-compose.yml        # postgres + backend + frontend
├── .env.example              # variables for docker compose
├── docs/ARCHITECTURE.md
├── backend/
│   ├── app/
│   │   ├── main.py           # app factory, CORS, error handlers
│   │   ├── core/             # settings, JWT verification, HTTP errors
│   │   ├── db/               # engine/session, declarative base
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # business logic: permissions, lead conversion, deals, reports, audit, notifications
│   │   ├── api/routes/       # one router per feature
│   │   ├── dependencies/     # auth (current user, roles), pagination
│   │   └── utils/            # search / sort / paginate helpers
│   ├── alembic/              # migrations
│   ├── scripts/seed.py       # demo data
│   └── tests/                # pytest suite
└── frontend/src/
    ├── app/                  # routes: (auth) pages, (app) pages, auth/callback
    ├── proxy.ts              # Next.js 16 "middleware": session refresh + redirects
    ├── components/ui/        # shadcn/ui primitives
    ├── components/shared/    # DataTable, Pagination, filters, KanbanBoard, ActivityTimeline, BarChart, dialogs…
    ├── features/<module>/    # module views, forms and TanStack Query hooks
    ├── services/             # typed Axios API calls
    ├── hooks/ lib/ types/ utils/
```

---

## Database

| Table | Purpose |
|---|---|
| `profiles` | App users (id = Supabase user id), role, active flag |
| `companies` | Accounts |
| `contacts` | People; optional company; `tags text[]` |
| `leads` | Prospects; source, status, score; `converted_*_id` after conversion |
| `pipelines`, `pipeline_stages` | Stages with order, default probability and type (open / won / lost) |
| `deals` | Value, currency, stage, status (mirrors stage type), probability, dates, company/contact links |
| `activities` | Calls, meetings, emails — linked to contact/company/lead/deal via nullable foreign keys |
| `notes` | Free-text notes with the same links |
| `tasks` | Due date, priority, status, assignee, links |
| `notifications` | Per-user in-app notifications |
| `audit_logs` | Action, entity, user, JSONB details (field changes, stage from/to) |

All tables use UUID primary keys, `created_at`/`updated_at` timestamps, foreign keys and indexes on common filters.
Enum-like columns are stored as `VARCHAR` and validated by Pydantic, which keeps migrations simple.

---

## Getting started

### 1. Supabase setup

1. Create a free project at [supabase.com](https://supabase.com).
2. **Project Settings → API**: copy the **Project URL** and the **publishable (anon) key**.
   (New projects sign tokens with asymmetric keys, which FastAPI verifies via the public JWKS endpoint.
   Projects on the **legacy JWT secret** must also set `SUPABASE_JWT_SECRET`.)
3. **Authentication → URL Configuration**: set Site URL to `http://localhost:3000` and add
   `http://localhost:3000/auth/callback` to the redirect URLs (used by email confirmation and password reset).
4. Optional for local testing: **Authentication → Sign In / Providers → Email** — turn off "Confirm email" to sign up without verifying.

No service-role key is used anywhere.

### 2a. Run with Docker (recommended)

```bash
cp .env.example .env          # fill in SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY
docker compose up --build
```

- Frontend: http://localhost:3000 · API: http://localhost:8000 · API docs: http://localhost:8000/docs
- Migrations run automatically when the backend container starts.
- Load demo data: `docker compose exec backend python -m scripts.seed`

### 2b. Run locally (hot reload)

Requirements: Python 3.12, Node 22, and PostgreSQL (e.g. `docker compose up db`, exposed on port **5433**).

**Backend**

```bash
cd backend
python -m venv myvenv
myvenv\Scripts\activate            # macOS/Linux: source myvenv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # set DATABASE_URL, SUPABASE_URL (and SUPABASE_JWT_SECRET if legacy)
alembic upgrade head
python -m scripts.seed             # optional demo data
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local         # set NEXT_PUBLIC_SUPABASE_URL / _PUBLISHABLE_KEY / NEXT_PUBLIC_API_URL
npm run dev
```

Open http://localhost:3000, sign up, and you'll land on the dashboard as Admin.

### Environment variables

| Where | Variable | Description |
|---|---|---|
| `backend/.env` | `DATABASE_URL` | e.g. `postgresql+psycopg://nexa:nexa@localhost:5433/nexa_crm` |
| | `SUPABASE_URL` | Project URL (used to fetch JWKS public keys) |
| | `SUPABASE_JWT_SECRET` | Only for projects on the legacy HS256 secret |
| | `CORS_ORIGINS` | Comma-separated allowed origins, default `http://localhost:3000` |
| `frontend/.env.local` | `NEXT_PUBLIC_SUPABASE_URL` | Project URL |
| | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Publishable/anon key (safe in the browser) |
| | `NEXT_PUBLIC_API_URL` | e.g. `http://localhost:8000/api` |
| `.env` (compose) | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWT_SECRET` | Passed to both containers |

### Migrations

```bash
cd backend
alembic upgrade head                                   # apply
alembic revision --autogenerate -m "describe change"   # after changing models
alembic downgrade -1                                   # roll back one
```

### Seed data

`python -m scripts.seed` loads 5 demo team members, ~22 companies, ~65 contacts, ~35 leads (10 converted),
~42 deals across every stage, ~115 activities, notes and ~36 tasks (overdue, due soon, completed).
It refuses to run on a non-empty database; `--reset` wipes CRM data (keeping real users) and reseeds.
Demo users can't log in — they exist so the team views and reports have data. Sign in first, then run
`--reset` if you also want records assigned to your own account.

---

## API

Interactive docs at **`/docs`** (Swagger) and `/redoc`. All endpoints are under `/api` and require
`Authorization: Bearer <supabase access token>` except `/api/health`.

| Resource | Endpoints |
|---|---|
| Users | `GET/PATCH /me`, `GET /users`, `PATCH /users/{id}` (admin) |
| Companies | `GET/POST /companies`, `GET/PATCH/DELETE /companies/{id}`, `GET /companies/options`, `GET /companies/industries` |
| Contacts | `GET/POST /contacts`, `GET/PATCH/DELETE /contacts/{id}`, `GET /contacts/options`, `GET /contacts/tags` |
| Leads | `GET/POST /leads`, `GET/PATCH/DELETE /leads/{id}`, `POST /leads/{id}/convert` |
| Pipelines | `GET /pipelines`, `POST /pipelines` (admin), `PATCH /pipelines/stages/{id}` (admin) |
| Deals | `GET/POST /deals`, `GET/PATCH/DELETE /deals/{id}`, `PATCH /deals/{id}/stage`, `GET /deals/board` |
| Activities / Notes | `GET/POST /activities`, `PATCH/DELETE /activities/{id}`; same for `/notes` |
| Timeline | `GET /timeline?contact_id=` (or `company_id`, `lead_id`, `deal_id`) |
| Tasks | `GET/POST /tasks`, `GET/PATCH/DELETE /tasks/{id}` |
| Dashboard & reports | `GET /dashboard/summary`, `GET /reports/{lead-conversion, pipeline, revenue, win-loss, rep-performance, lead-sources}?start_date=&end_date=` |
| Notifications | `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all` |
| Audit log | `GET /audit-logs` (manager/admin) |

List endpoints accept `page`, `page_size` (≤100), `search`, `sort_by`, `sort_order` plus resource filters, and
return `{ items, total, page, page_size, pages }`. Errors are `{ "detail": "…" }` with 400/401/403/404/409/422.

---

## Testing

```bash
cd backend
pytest
```

71 tests run against a real PostgreSQL test database (`nexa_crm_test`, created by `docker/postgres/init.sql`;
override with `TEST_DATABASE_URL`). Each test runs in a rolled-back transaction, and tokens are signed locally
with a test secret, so the real authentication dependency is exercised without calling Supabase.

Covered: authentication (missing/invalid/expired/wrong-audience tokens, just-in-time profiles, deactivated users),
role and ownership permissions, CRUD and validation, search/filter/sort/pagination, lead conversion,
deal stage moves and Kanban board, tasks and timeline, reports, notifications and audit logging.

Frontend checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

---

## Future improvements

Planned for a separate **"Scalability & Production Optimization"** phase, intentionally left out of the core build:

- Redis caching for dashboard/report queries; background jobs (e.g. scheduled task reminders, email notifications)
- Query optimization (covering indexes, materialized report views), full-text search
- Rate limiting, structured logging, error monitoring (Sentry), metrics
- CI/CD pipeline, cloud deployment, horizontal scaling behind a load balancer
- Multi-currency reporting with exchange rates; multiple pipelines in the UI; custom fields; CSV import/export
- Email/calendar integrations; realtime updates via websockets or Supabase Realtime
