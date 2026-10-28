# Cloud, Integrations & Operations

> **Current state: NexaCRM is not deployed anywhere and has no CI/CD.** It runs locally. The external services
> are **Supabase Auth** and, for the AI assistant, the **Google Gemini API** (unless a local Ollama model is used).
> Everything under "Target architecture" is a plan for the future "Scalability & Production Optimization"
> phase — do not implement any of it unless the user asks.

## Current architecture

```
Browser ──▶ Next.js dev server :3000 ──(Axios, Bearer JWT)──▶ FastAPI (uvicorn) :8000 ──▶ PostgreSQL 18 :5432 (local)
   └──────────────(sign-up / login / reset)──────────────▶ Supabase Auth (hosted project)
                                                   FastAPI ──(JWKS fetch, cached)──▶ Supabase /auth/v1/.well-known/jwks.json
                                                   FastAPI ──(/api/assistant/chat)──▶ Gemini API  or  Ollama :11434 (local)
```

### Container setup (available, optional)

- `docker-compose.yml`: `db` (`postgres:17-alpine`, host port **5433**, volume `postgres_data`, `docker/postgres/init.sql` creates `nexa_crm_test`), `backend` (runs migrations then uvicorn on 8000), `frontend` (standalone Next.js on 3000, `NEXT_PUBLIC_*` passed as build args).
- It reads a **root `.env`** (template: root `.env.example`): `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWT_SECRET`, plus the AI assistant variables `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, which are passed to the `backend` service's `environment` with the same defaults as `app/core/config.py`. `backend/.dockerignore` excludes `backend/.env`, so the container gets its settings only from compose.
- `GEMINI_FALLBACK_MODEL` uses `${VAR-default}` (not `:-`), so an explicitly empty value in `.env` still disables the fallback.
- Ollama is expected on the **host**: `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434`, and the backend has `extra_hosts: host.docker.internal:host-gateway` so that name also resolves on Linux.
- The images have never been built/run end to end (Docker Desktop wasn't available when written); `docker compose config` validates and the standalone frontend server was smoke-tested. The user's day-to-day workflow does **not** use Docker.

## Third-party services

| Service | Used for | Where configured | Notes |
|---|---|---|---|
| **Supabase Auth** | Sign-up, login, logout, email verification, password reset, session refresh, JWT issuing | Frontend: `src/lib/supabase/{client,server,proxy,config}.ts`, `src/app/auth/callback/route.ts`, `src/features/auth/*`. Backend: `app/core/security.py` | PKCE flow via `@supabase/ssr`; email links → `/auth/callback?next=…` (relative redirects only). Supabase's database is **not** used for CRM data. |
| **Google Gemini API** | Chat model for the AI assistant (`LLM_PROVIDER=gemini`, default) | Backend: `app/services/assistant/llm.py`, `GEMINI_API_KEY` / `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | Called server-side only. The conversation, the system prompt (user's name, today's date) and tool results (matching CRM records) are sent to Google. Free-tier quotas are per model and per day; the fallback model takes over on rate-limit/overload errors. |
| **Ollama** (optional, local) | Alternative chat model (`LLM_PROVIDER=ollama`, e.g. `qwen3:4b`) | `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Runs on the user's machine; no CRM data leaves it. |
| Google Fonts (via `next/font`) | Geist fonts | `src/app/layout.tsx` | Self-hosted by Next.js at build time |

No email provider, payments, analytics, file storage or other APIs are integrated.

## Authentication & secrets management

- **Token flow:** Supabase session lives in cookies → `src/proxy.ts` calls `supabase.auth.getClaims()` on each navigation (refreshes/validates, redirects signed-out users to `/login?next=…`) → the Axios request interceptor reads `getSession()` and sends `Authorization: Bearer <access_token>` → FastAPI verifies signature, `exp`, `aud=authenticated`, requires `sub`.
- **Key types:** asymmetric (RS256/ES256) tokens are verified with the JWKS (`PyJWKClient`, keys cached in-process); legacy HS256 tokens with `SUPABASE_JWT_SECRET`. Other algorithms are rejected.
- **On 401** the frontend signs out and hard-navigates to `/login`.
- **Secrets inventory:**

| Secret | Lives in | Exposure |
|---|---|---|
| PostgreSQL password | `backend/.env` (`DATABASE_URL`) | Server only |
| `SUPABASE_JWT_SECRET` (if legacy) | `backend/.env` | Server only — never log it |
| `GEMINI_API_KEY` | `backend/.env` | Server only — never send it to the frontend or log it |
| Supabase publishable/anon key | `frontend/.env(.local)` as `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Public by design (browser) |
| Supabase service-role key | — | **Not used. Never add it.** |

- All real `.env` files are gitignored (`backend/.gitignore`, `frontend/.gitignore` `.env*` with `!.env.example`, root `.gitignore`). Only `*.env.example` files are committed, with placeholders.
- In any future deployment, secrets go into the platform's secret store / environment settings — never into images, `NEXT_PUBLIC_*`, or the repo.

## Logging & monitoring (current)

- **Backend:** uvicorn access logs to stdout. App logger `logging.getLogger("nexa_crm")` in `app/main.py`: `IntegrityError` → warning + HTTP 409; any unhandled exception → `logger.exception` + generic HTTP 500 (`{"detail": "Something went wrong on our side…"}` — internals are never returned to the client).
- **Frontend:** API errors are turned into readable toasts by `getErrorMessage()` (`src/lib/api-client.ts`); `src/app/(app)/error.tsx` catches render errors and logs to the console.
- **AI assistant:** model failures are logged as `logger.warning("Assistant model error (<provider>): …")` and returned to the client as a readable 502; tool errors go back to the model, not the log.
- **Health check:** `GET /api/health` → `{"status": "ok"}` (does not touch the database).
- **Audit trail:** business actions are recorded in `audit_logs` and viewable in Settings → Audit log (manager/admin).
- No metrics, tracing, uptime monitoring or error tracking service is set up.

## Target architecture (future phase — plan only)

When the user starts the "Scalability & Production Optimization" phase, the intended direction is:

| Concern | Proposed approach |
|---|---|
| Frontend hosting | Container from `frontend/Dockerfile` (or Vercel); set `NEXT_PUBLIC_*` at build time |
| Backend hosting | Container from `backend/Dockerfile` on a managed container platform; run `alembic upgrade head` as a release step rather than on every container start once there are multiple replicas. `Settings` already accepts the `postgres://` / `postgresql://` URLs that hosts like Render hand out (rewritten to `postgresql+psycopg://`) |
| Database | Managed PostgreSQL with automated backups; separate DBs per environment |
| CI (GitHub Actions on `akashdabhane/nexa-crm`) | On PR: backend `pytest` with a `postgres` service container; frontend `npm ci`, `tsc --noEmit`, `npm run lint`, `npm run build` |
| CD | Build & push images on merge to `main`; deploy staging, then promote to production |
| Config | `CORS_ORIGINS` set to real frontend origins; Supabase Site URL/redirects per environment |
| Observability | Structured JSON logs, error tracking (e.g. Sentry), request metrics/latency, DB slow-query logging, uptime check on `/api/health` |
| Performance & scale | Candidates from the roadmap: Redis caching for dashboard/report aggregates, background jobs for reminders/email, rate limiting (especially `/api/assistant/chat`, which spends paid/limited LLM quota), query/index tuning, horizontal API replicas |
| AI | Paid Gemini tier or a hosted model for production quotas; per-user usage limits |

Each of these is a separate, user-approved change; none should leak into feature work.
