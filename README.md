# NexaCRM

A full-stack CRM for small sales teams: contacts, companies, leads, deals, a Kanban sales pipeline,
activities, tasks, notes, notifications, reports, an audit log, and an **AI assistant** that turns plain-language
notes about your sales work into CRM records. It's inspired by the core of HubSpot and kept simple enough to
understand end to end.

**Stack:** Next.js 16 · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query · FastAPI · SQLAlchemy 2 ·
Alembic · PostgreSQL · Supabase Auth · LangGraph + LangChain (Google Gemini or a local Ollama model) · Docker Compose

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
| **AI assistant** | "AI Assistant" button in the top bar opens a chat panel. Describe calls, cold emails, meetings, new prospects and follow-ups in your own words; the assistant searches for existing records first (no duplicates), then creates or updates leads, contacts, companies, activities, notes and tasks, and links to everything it saved. It uses the same permissions, validation, audit trail and notifications as the UI |
| **Auth & roles** | Supabase sign-up, login, email verification, password reset. Roles: Admin, Manager, Sales Rep |

### Roles

| | Admin | Manager | Sales Rep |
|---|:-:|:-:|:-:|
| View all records | ✅ | ✅ | ✅ |
| Create records (in the UI or through the AI assistant) | ✅ | ✅ | ✅ (owned by themselves) |
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
                                  - /api/assistant/chat ──▶ LangGraph agent ──▶ Gemini API or local Ollama
```

- **Supabase is only the identity provider.** All CRM data lives in our PostgreSQL, owned by SQLAlchemy/Alembic.
  FastAPI never sees passwords; it verifies Supabase-signed tokens and keeps an app-side `profiles` table for roles.
- **Synchronous SQLAlchemy** keeps the code simple to read and debug. FastAPI runs sync endpoints in a thread pool.
- **No background workers.** Task-due notifications are created lazily when a user loads notifications; the bell polls every 60s.
- **Server-side search, filtering, sorting and pagination** for every list; sort columns are whitelisted.
- **The AI assistant is a LangGraph agent** (`backend/app/services/assistant/`). The model loops "think → call tools →
  read results" until it answers in plain text. Its LangChain tools call the same route functions as the REST API, so a record
  created by chat is validated, permission-checked, audited and notified exactly like one created in the UI. The
  server keeps no chat state: the browser sends the whole conversation with every message. The model is chosen in
  `backend/.env`: `LLM_PROVIDER=gemini` (Google Gemini, with an automatic fallback model when the main one is
  overloaded or out of quota) or `LLM_PROVIDER=ollama` (a local model such as `qwen3:4b`).

More detail (schema, ER diagram, design decisions): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Project structure

```
nexa-crm/
├── docker-compose.yml        # postgres + backend + frontend (optional)
├── .env.example              # variables for docker compose (copy to .env)
├── docker/postgres/init.sql  # creates the nexa_crm_test database
├── docs/                     # ARCHITECTURE.md, USER_GUIDE.md and the context files (purpose, ai, tech-stack,
│                             # design, rules, production, cloud, contributing)
├── backend/
│   ├── app/
│   │   ├── main.py           # app factory, CORS, error handlers
│   │   ├── core/             # settings, JWT verification, HTTP errors
│   │   ├── db/               # engine/session, declarative base
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # business logic: permissions, lead conversion, deals, reports, audit, notifications
│   │   │   └── assistant/    # AI assistant: agent.py (LangGraph), tools.py (LangChain tools), llm.py (Gemini/Ollama)
│   │   ├── api/routes/       # one router per feature
│   │   ├── dependencies/     # auth (current user, roles), pagination
│   │   └── utils/            # search / sort / paginate helpers
│   ├── alembic/              # migrations
│   ├── scripts/seed.py       # demo data (--reset, --clear)
│   └── tests/                # pytest suite
└── frontend/src/
    ├── app/                  # routes: (auth) pages, (app) pages, auth/callback
    ├── proxy.ts              # Next.js 16 "middleware": session refresh + redirects
    ├── components/ui/        # shadcn/ui primitives
    ├── components/shared/    # DataTable, Pagination, filters, KanbanBoard, ActivityTimeline, BarChart, dialogs…
    ├── features/<module>/    # module views, forms and TanStack Query hooks (incl. assistant/ chat panel)
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
Enum-like columns are stored as `VARCHAR` and validated by Pydantic, which keeps migrations simple. The AI
assistant adds no tables: it stores nothing of its own, only the CRM records it creates.

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

### 2. AI assistant setup (optional)

The rest of the CRM works without it; the chat panel shows an error until a model is configured. Pick one:

- **Google Gemini** (default): create an API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
  and set `GEMINI_API_KEY` in `backend/.env`. The default model is `gemini-3.5-flash-lite`, which gets a far bigger
  free-tier daily quota than Flash; `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash`) is tried when the main model
  is overloaded or out of quota.
- **Ollama** (local, free, no data leaves your machine): install [Ollama](https://ollama.com), run
  `ollama pull qwen3:4b`, and set `LLM_PROVIDER=ollama` in `backend/.env`.

### 3a. Run locally (hot reload, primary workflow)

Requirements: Python 3.12, Node 22, and PostgreSQL (a local install on port 5432, or `docker compose up db`,
exposed on port **5433**). Create the two databases once: `nexa_crm` and `nexa_crm_test` (the compose `db`
service creates both).

**Backend**

```bash
cd backend
python -m venv myvenv
myvenv\Scripts\activate            # macOS/Linux: source myvenv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # set DATABASE_URL, SUPABASE_URL (+ SUPABASE_JWT_SECRET if legacy, GEMINI_API_KEY)
alembic upgrade head
python -m scripts.seed             # optional demo data, empty database only
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

### 3b. Run with Docker

```bash
cp .env.example .env          # fill in SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and (for the assistant) GEMINI_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000 · API: http://localhost:8000 · API docs: http://localhost:8000/docs
- Migrations run automatically when the backend container starts.
- Load demo data: `docker compose exec backend python -m scripts.seed`
- The compose stack has its own database (`nexa_crm` in the `db` container), separate from a local PostgreSQL install.
- AI assistant with Ollama: run Ollama on your machine (not in Docker) and set `LLM_PROVIDER=ollama` in `.env`.
  The backend container reaches it at `http://host.docker.internal:11434` (the default in `.env.example`).

### Environment variables

| Where | Variable | Description |
|---|---|---|
| `backend/.env` | `DATABASE_URL` | e.g. `postgresql+psycopg://postgres:<password>@localhost:5432/nexa_crm`. `postgres://` and `postgresql://` URLs (as given by hosts like Render) are rewritten to the psycopg driver automatically |
| | `SUPABASE_URL` | Project URL (used to fetch JWKS public keys) |
| | `SUPABASE_JWT_SECRET` | Only for projects on the legacy HS256 secret |
| | `CORS_ORIGINS` | Comma-separated allowed origins, default `http://localhost:3000` |
| | `LLM_PROVIDER` | AI assistant model: `gemini` (default) or `ollama` |
| | `GEMINI_API_KEY` | Google AI Studio key; required when `LLM_PROVIDER=gemini` |
| | `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | Default `gemini-3.5-flash-lite` / `gemini-3.5-flash`; leave the fallback empty to disable it |
| | `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Default `http://localhost:11434` / `qwen3:4b` |
| | `TEST_DATABASE_URL` | Optional; tests default to `DATABASE_URL` with the database name `nexa_crm_test` |
| `frontend/.env.local` | `NEXT_PUBLIC_SUPABASE_URL` | Project URL |
| | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Publishable/anon key (safe in the browser) |
| | `NEXT_PUBLIC_API_URL` | e.g. `http://localhost:8000/api` |
| `.env` (compose, from `.env.example`) | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWT_SECRET` | Supabase values for both containers |
| | `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Passed to the backend container; same meaning as in `backend/.env`, except `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434` |

### Migrations

```bash
cd backend
alembic upgrade head                                   # apply
alembic revision --autogenerate -m "describe change"   # after changing models
alembic downgrade -1                                   # roll back one
```

### Seed data

> ⚠️ Every seed mode writes to the database in `DATABASE_URL`. Once you use NexaCRM for real data, don't run
> `--reset` or `--clear` against it, because both delete CRM records.

`python -m scripts.seed` loads 5 demo team members, ~22 companies, ~65 contacts, ~35 leads (10 converted),
~42 deals across every stage, ~115 activities, notes and ~36 tasks (overdue, due soon, completed).
It refuses to run on a non-empty database; `--reset` wipes CRM data (keeping real users) and reseeds.
Demo users can't log in — they exist so the team views and reports have data. Sign in first, then run
`--reset` if you also want records assigned to your own account.

`python -m scripts.seed --clear` removes all CRM records and the demo users, leaving an empty CRM for
your own data. Real accounts, their roles and the pipeline stages are kept.

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for how to enter your data and use each feature.

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
| AI assistant | `POST /assistant/chat` with `{ messages: [{ role, content, records? }] }` (≤ 50 messages, last one from the user) → `{ reply, records }` |

List endpoints accept `page`, `page_size` (≤100), `search`, `sort_by`, `sort_order` plus resource filters, and
return `{ items, total, page, page_size, pages }`. Errors are `{ "detail": "…" }` with 400/401/403/404/409/422;
the assistant also returns **502** when the model fails (quota, timeout, Ollama not running) and **503** when
Gemini is selected but `GEMINI_API_KEY` is missing.

---

## Testing

```bash
cd backend
pytest
```

84 tests run against a real PostgreSQL test database (`nexa_crm_test`, created by `docker/postgres/init.sql`;
override with `TEST_DATABASE_URL`). Each test runs in a rolled-back transaction, and tokens are signed locally
with a test secret, so the real authentication dependency is exercised without calling Supabase. The assistant
tests swap the chat model for a scripted fake, so they never call Gemini or Ollama.

Covered: authentication (missing/invalid/expired/wrong-audience tokens, clock-skew leeway, just-in-time profiles,
deactivated users), role and ownership permissions, CRUD and validation, search/filter/sort/pagination, lead
conversion, deal stage moves and Kanban board, tasks and timeline, reports, notifications and audit logging,
settings (database URL normalisation), and the AI assistant (records saved through tools, tool errors fed back to
the model, permissions, conversation history, fallback model, partial saves when the model fails, provider config).

Frontend checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

---

## Future improvements

These are planned for a separate **"Scalability & Production Optimization"** phase and were left out of the core build on purpose:

- Redis caching for dashboard/report queries; background jobs (e.g. scheduled task reminders, email notifications)
- Query optimization (covering indexes, materialized report views), full-text search
- Rate limiting (including on the AI assistant), structured logging, error monitoring (Sentry), metrics
- CI/CD pipeline, cloud deployment, horizontal scaling behind a load balancer
- Multi-currency reporting with exchange rates; multiple pipelines in the UI; custom fields; CSV import/export
- Email/calendar integrations; realtime updates via websockets or Supabase Realtime
- AI assistant: streamed replies, deal creation and lead conversion through chat, saved chat history
