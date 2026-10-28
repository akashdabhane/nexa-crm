# Build, Test & Delivery

How to build, test and verify NexaCRM before handing work over. Nothing counts as "done" until the relevant
checks below have been run and passed.

## Environment setup

### Backend — `backend/.env` (copy from `backend/.env.example`; gitignored)

| Variable | Required | Example / notes |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+psycopg://postgres:<password>@localhost:5432/nexa_crm` (local PostgreSQL 18). `postgres://…` and `postgresql://…` are rewritten to `postgresql+psycopg://` by a validator in `app/core/config.py`. |
| `SUPABASE_URL` | ✅ | `https://<ref>.supabase.co` — used to fetch the JWKS for RS256/ES256 tokens |
| `SUPABASE_JWT_SECRET` | only for legacy HS256 projects | Supabase → Project Settings → API → JWT secret |
| `CORS_ORIGINS` | optional | Comma-separated; default `http://localhost:3000` |
| `LLM_PROVIDER` | optional | `gemini` (default) or `ollama` — the AI assistant's chat model |
| `GEMINI_API_KEY` | for the assistant with Gemini | https://aistudio.google.com/apikey. Missing → `/api/assistant/chat` answers 503; the rest of the app works |
| `GEMINI_MODEL` | optional | Default `gemini-3.5-flash-lite` (much larger free-tier daily quota than Flash) |
| `GEMINI_FALLBACK_MODEL` | optional | Default `gemini-3.5-flash`; tried on rate-limit/overload/timeout errors. Empty disables it |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | optional | Default `http://localhost:11434` / `qwen3:4b` (run `ollama pull qwen3:4b` first) |
| `TEST_DATABASE_URL` | optional | Defaults to `DATABASE_URL` with the DB name replaced by `nexa_crm_test` |

Settings are loaded by `app/core/config.py` (pydantic-settings). **Process environment variables override `.env`**
— if the app connects to the wrong database, check for a stray `DATABASE_URL` in your shell first.

### Frontend — `frontend/.env.local` or `frontend/.env` (copy from `frontend/.env.example`; gitignored)

| Variable | Example |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | publishable/anon key (safe for the browser) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` |

`NEXT_PUBLIC_*` values are **inlined at build time** — rebuild after changing them. Without the Supabase values the
login page shows a "Supabase is not configured" notice instead of crashing.

### Supabase dashboard

Authentication → URL Configuration: Site URL `http://localhost:3000`, redirect URL
`http://localhost:3000/auth/callback` (email confirmation and password reset land there).

## Local run (primary workflow — no Docker)

```bash
# one-time
psql -U postgres -c "CREATE DATABASE nexa_crm;" -c "CREATE DATABASE nexa_crm_test;"

# backend
cd backend
myvenv\Scripts\activate                      # macOS/Linux: source myvenv/bin/activate
pip install -r requirements.txt
alembic upgrade head
# python -m scripts.seed                     # demo data, EMPTY databases only; --reset/--clear delete CRM data
uvicorn app.main:app --reload                # http://localhost:8000 · docs at /docs

# frontend
cd frontend
npm install
npm run dev                                  # http://localhost:3000
```

Symptom → cause: **every API request stays "pending"** while `/api/health` answers → the backend can't reach
PostgreSQL (wrong host/port in `DATABASE_URL`). The engine uses `connect_timeout=5`, so this now surfaces as an
error within seconds; restart `uvicorn` after editing `.env` (the reloader only watches `.py` files).

## Build & bundling

- **Frontend:** `npm run build` (Next.js 16 + Turbopack). `next.config.ts` sets `output: "standalone"`, producing `.next/standalone/server.js` for the Docker image (`frontend/Dockerfile`, multi-stage, `node:22-alpine`, copies `.next/static` and `public`). Pages are client-rendered views inside thin server `page.tsx` files; routes using `useSearchParams` are wrapped in `<Suspense>` so the build can prerender.
- **Backend:** no build step. `backend/Dockerfile` installs `requirements.txt` and runs `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Optimization stance:** don't optimize prematurely. Existing, sufficient measures: SQL-side pagination/filtering, grouped count queries for company stats (no N+1), joined/selectin eager loading on relationships, TanStack Query `staleTime: 30s` + `keepPreviousData` for lists, 300ms debounced search.

## Testing strategy

| Layer | Tooling | Status |
|---|---|---|
| Backend API + business rules | `pytest` + FastAPI `TestClient` against **real PostgreSQL** (`nexa_crm_test`) | ✅ 84 tests in `backend/tests/` |
| Frontend static checks | `tsc --noEmit` (strict), ESLint (next core-web-vitals + typescript, incl. React Compiler rules) | ✅ must be clean |
| Frontend unit / component tests | — | ❌ not set up (don't add Jest/Vitest without asking) |
| End-to-end | — | ❌ not set up (Playwright is the likely future choice; ask first) |
| Manual browser verification | Running app, signed in with a real Supabase account | Required for UI changes |

How the backend tests work (`backend/tests/conftest.py`):
- The schema is created with `Base.metadata.create_all` once per session and dropped afterwards.
- Each test runs inside a connection-level transaction with `join_transaction_mode="create_savepoint"` and is **rolled back**, so app code can `commit()` freely.
- Tokens are **HS256-signed locally** with a test secret (`make_token`, `auth_headers`), so the real `get_current_user` dependency runs without Supabase. Fixtures: `admin`, `manager`, `rep`, `other_rep`.
- Test files by area: `test_auth.py`, `test_companies_contacts.py`, `test_leads.py`, `test_deals.py`, `test_activities_tasks.py`, `test_reports.py`, `test_notifications_audit.py`, `test_config.py` (settings), `test_assistant.py` (AI assistant).
- `test_assistant.py` replaces the chat model with `ScriptedModel` (monkeypatching `llm._gemini` / `llm._ollama`), which plays back scripted tool calls and replies. The real LangGraph graph, tools, permissions and DB writes run, but **no request goes to Gemini or Ollama**. Keep it that way for new assistant tests.

Write a test for every new endpoint, business rule, permission rule or bug fix. Assert status codes **and** the
resulting data.

## Linting & formatting

- **Frontend:** `npm run lint` (ESLint 9 flat config `frontend/eslint.config.mjs`). Must report 0 errors and 0 warnings. No Prettier is configured — match the existing formatting (2-space indent, double quotes, semicolons, trailing commas, ~120-char lines).
- **Backend:** no linter/formatter is configured. Follow PEP 8 as written in the code (4 spaces, double quotes, ~120-char lines, sorted imports: stdlib → third-party → `app`). Don't reformat files you aren't changing.
- Do not add Prettier, Ruff, Black, mypy or pre-commit hooks without asking — proposing them is fine.

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "short description"   # after changing models (and importing them in app/models/__init__.py)
# REVIEW the generated file in alembic/versions/ (renames show up as drop+add; server defaults and data need hand edits)
alembic upgrade head
alembic downgrade -1                                       # to test the downgrade path
```

Never edit a migration that has already been applied/committed — add a new one.

## Dependency files

- `frontend/package.json` + `package-lock.json`: install with `npm install <pkg>` (only when approved); commit both files.
- `backend/requirements.txt`: currently a full `pip freeze` saved as **UTF-16** (PowerShell's `>` default), now including the LangChain/LangGraph packages and their transitive deps. pip reads it, but git and GitHub diff it as binary. When regenerating, write UTF-8: `pip freeze | Out-File -Encoding utf8 requirements.txt` (PowerShell) or `pip freeze > requirements.txt` from Git Bash. Keep versions pinned (`==`).

## Pre-delivery checklist

Run what applies to your change and report the results honestly:

```bash
cd backend  && pytest                                  # all green
cd frontend && npx tsc --noEmit && npm run lint        # no output / 0 problems
cd frontend && npm run build                           # succeeds
```

- [ ] New/changed models have a reviewed Alembic migration, applied locally.
- [ ] New endpoints have tests (happy path, validation 422/400, permission 403, not found 404 where relevant).
- [ ] UI change exercised in the running app (desktop and ~375px mobile width), including loading, empty and error states.
- [ ] Assistant changes: covered by `ScriptedModel` tests; any live chat check was run against `nexa_crm_test`, not the real database.
- [ ] No secrets, `.env` files, `myvenv/`, `node_modules/`, `.next/` or `__pycache__/` staged.
- [ ] Context `.md` files updated if the change affects them (see `contributing.md`).
