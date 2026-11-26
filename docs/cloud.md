# Cloud, Integrations & Operations

> **Current state: NexaCRM is deployed** — the frontend on **Vercel** (production domain
> `https://nexa-crm-eta.vercel.app`) and the backend on **Render**. There is **no CI/CD pipeline in this repository**
> (no `.github/workflows`). Day-to-day development still runs locally. The external services are **Supabase Auth**,
> the **Google Gemini API** for the AI assistant (unless a local Ollama model is used), the **Meta Graph API** for
> Facebook/Instagram lead ads (only when configured), and **Vercel Web Analytics**. Everything under "Target
> architecture" is a plan for the future "Scalability & Production Optimization" phase — do not implement any of it
> unless the user asks.

## Current architecture

```
Local:
Browser ──▶ Next.js dev server :3000 ──(Axios, Bearer JWT + X-Organization-Id)──▶ FastAPI (uvicorn) :8000 ──▶ PostgreSQL 18 :5432 (local)
   └──────────────(sign-up / login / reset)──────────────▶ Supabase Auth (hosted project)
                                                   FastAPI ──(JWKS fetch, cached)──▶ Supabase /auth/v1/.well-known/jwks.json
                                                   FastAPI ──(/api/assistant/chat)──▶ Gemini API  or  Ollama :11434 (local)
                                                   FastAPI ──(Meta Lead Ads, optional)──▶ graph.facebook.com

Deployed:
Browser ──▶ Vercel (Next.js, nexa-crm-eta.vercel.app) ──(Axios, NEXT_PUBLIC_API_URL)──▶ Render (FastAPI) ──▶ PostgreSQL (DATABASE_URL)
```

### Deployment (current)

- **Frontend — Vercel.** Environment variables set in the Vercel project: `NEXT_PUBLIC_API_URL` (production),
  `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (production + preview). Set
  `NEXT_PUBLIC_SITE_URL` to the production origin too, or canonical URLs, the sitemap and Open Graph images point at
  `http://localhost:3000`. `NEXT_PUBLIC_*` values are inlined at build time, so redeploy after changing them.
  `@vercel/analytics` (`<Analytics />` in `src/app/layout.tsx`) reports page views to Vercel Web Analytics.
- **Backend — Render.** Runs the FastAPI app; settings come from Render's environment. `Settings` rewrites the
  `postgres://` / `postgresql://` URLs Render hands out to `postgresql+psycopg://`. `CORS_ORIGINS` must contain the
  Vercel origin (the default, `http://localhost:3000,https://nexa-crm-eta.vercel.app`, already does; trailing slashes
  are stripped). If Render sets `CORS_ORIGINS` itself, that value replaces the default, so include the Vercel origin
  there. Swagger working on Render proves nothing about CORS (it's same-origin).
- **Supabase:** add the production origin and `<origin>/auth/callback` to Authentication → URL Configuration, next to
  the localhost ones.
- Migrations: the `backend/Dockerfile` command runs `alembic upgrade head` before starting uvicorn; if Render isn't
  started with that command, run the migration as a release step.

### Container setup (available, optional)

- `docker-compose.yml`: `db` (`postgres:17-alpine`, host port **5433**, volume `postgres_data`, `docker/postgres/init.sql` creates `nexa_crm_test`), `backend` (runs migrations then uvicorn on 8000), `frontend` (standalone Next.js on 3000, `NEXT_PUBLIC_*` passed as build args).
- It reads a **root `.env`**. There is **no root `.env.example` any more** (it was removed; the comment at the top of `docker-compose.yml` still mentions it), so create the file by hand with: `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (both required, compose fails without them), `SUPABASE_JWT_SECRET`, `SITE_URL` (optional, becomes `NEXT_PUBLIC_SITE_URL`), plus the AI assistant variables `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, which are passed to the `backend` service's `environment` with the same defaults as `app/core/config.py`. `CORS_ORIGINS` is fixed to `http://localhost:3000`. `backend/.dockerignore` excludes `backend/.env`, so the container gets its settings only from compose.
- Compose does **not** pass `INTEGRATIONS_SECRET`, `META_*` or `WHISPER_*`: inside the container social lead imports via Meta are unconfigured and voice input runs with the code defaults (Whisper `base` on CPU, downloaded on first use). Add them to the `backend` `environment` if you need them.
- `GEMINI_FALLBACK_MODEL` uses `${VAR-default}` (not `:-`), so an explicitly empty value in `.env` still disables the fallback.
- Ollama is expected on the **host**: `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434`, and the backend has `extra_hosts: host.docker.internal:host-gateway` so that name also resolves on Linux.
- The images have never been built/run end to end (Docker Desktop wasn't available when written); `docker compose config` validates and the standalone frontend server was smoke-tested. The user's day-to-day workflow does **not** use Docker.

## Third-party services

| Service | Used for | Where configured | Notes |
|---|---|---|---|
| **Supabase Auth** | Sign-up, login, logout, email verification, password reset, session refresh, JWT issuing | Frontend: `src/lib/supabase/{client,server,proxy,config}.ts`, `src/app/auth/callback/route.ts`, `src/features/auth/*`. Backend: `app/core/security.py` | PKCE flow via `@supabase/ssr`; email links → `/auth/callback?next=…` (relative redirects only). Supabase's database is **not** used for CRM data. |
| **Google Gemini API** | Chat model for the AI assistant (`LLM_PROVIDER=gemini`, default) | Backend: `app/services/assistant/llm.py`, `GEMINI_API_KEY` / `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | Called server-side only. The conversation, the system prompt (user's name, today's date) and tool results (matching CRM records) are sent to Google. Free-tier quotas are per model and per day; the fallback model takes over on rate-limit/overload errors. |
| **Ollama** (optional, local) | Alternative chat model (`LLM_PROVIDER=ollama`, e.g. `qwen3:4b`) | `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Runs on the user's machine; no CRM data leaves it. |
| **Meta Graph API** (optional) | Facebook/Instagram Lead Ads: validate the Page token, subscribe the Page to `leadgen`, fetch leads (`Sync now` and the webhook) | Backend: `app/services/meta_leads.py`, `app/api/routes/integrations.py`; `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_GRAPH_VERSION`, `INTEGRATIONS_SECRET` | Meta calls `POST /api/integrations/meta/webhook` (signature checked with `X-Hub-Signature-256`). Page tokens are stored Fernet-encrypted. Generic webhooks (`/api/integrations/webhooks/{token}`) are called by Zapier/Make/n8n etc. |
| **Hugging Face Hub** | One-off download of the Whisper model for voice input (`WHISPER_MODEL`) | `app/services/assistant/speech.py` (faster-whisper) | Only the model is downloaded; audio is transcribed on the API server and never sent anywhere. |
| **Vercel Web Analytics** | Page-view analytics on the deployed frontend | `@vercel/analytics`, `src/app/layout.tsx` | Active only on Vercel deployments. |
| Google Fonts (via `next/font`) | Geist fonts | `src/app/layout.tsx` | Self-hosted by Next.js at build time |

No email provider, payments, file storage or other APIs are integrated. (Invitations are not emailed: the invited
person sees them on the Organizations page after signing in with that address.)

## Authentication & secrets management

- **Token flow:** Supabase session lives in cookies → `src/proxy.ts` calls `supabase.auth.getClaims()` on each navigation (refreshes/validates, redirects signed-out users to `/login?next=…`; `/`, `/login`, `/signup`, `/forgot-password` and `/auth/*` are public, and signed-in users visiting `/` or an auth page go to `/dashboard`) → the Axios request interceptor reads `getSession()` and sends `Authorization: Bearer <access_token>` and `X-Organization-Id` → FastAPI verifies signature, `exp`, `aud=authenticated`, requires `sub`, then checks the organization membership.
- **Key types:** asymmetric (RS256/ES256) tokens are verified with the JWKS (`PyJWKClient`, keys cached in-process); legacy HS256 tokens with `SUPABASE_JWT_SECRET`. Other algorithms are rejected.
- **On 401** the frontend clears the active organization, signs out and hard-navigates to `/login`. **On an `X-Organization-Error` response** (no organization selected, not a member, membership disabled) it clears the active organization and hard-navigates to `/organizations`. `CORS` exposes that header (`expose_headers` in `app/main.py`).
- **Secrets inventory:**

| Secret | Lives in | Exposure |
|---|---|---|
| PostgreSQL password | `backend/.env` (`DATABASE_URL`) | Server only |
| `SUPABASE_JWT_SECRET` (if legacy) | `backend/.env` | Server only — never log it |
| `GEMINI_API_KEY` | `backend/.env` | Server only — never send it to the frontend or log it |
| `INTEGRATIONS_SECRET` | `backend/.env` | Server only. Encrypts stored Meta Page tokens; changing it makes them unreadable (re-enter them) |
| `META_APP_SECRET`, `META_VERIFY_TOKEN` | `backend/.env` | Server only |
| Meta Page access tokens | `lead_integrations.access_token_encrypted` (Fernet) | Never returned by the API |
| Integration webhook tokens | `lead_integrations.webhook_token` | Secret part of a public URL; shown to admins in Settings → Lead sources; rotate if leaked |
| Supabase publishable/anon key | `frontend/.env(.local)` as `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Public by design (browser) |
| Supabase service-role key | — | **Not used. Never add it.** |

- All real `.env` files are gitignored (`backend/.gitignore`, `frontend/.gitignore` `.env*` with `!.env.example`, root `.gitignore`). Only `*.env.example` files are committed, with placeholders.
- In the Vercel / Render deployment (and any future one), secrets go into the platform's environment settings — never into images, `NEXT_PUBLIC_*`, or the repo.

## Logging & monitoring (current)

- **Backend:** uvicorn access logs to stdout. App logger `logging.getLogger("nexa_crm")` in `app/main.py`: `IntegrityError` → warning + HTTP 409; any unhandled exception → `logger.exception` + generic HTTP 500 (`{"detail": "Something went wrong on our side…"}` — internals are never returned to the client).
- **Frontend:** API errors are turned into readable toasts by `getErrorMessage()` (`src/lib/api-client.ts`); `src/app/(app)/error.tsx` catches render errors and logs to the console.
- **AI assistant:** model failures are logged as `logger.warning("Assistant model error (<provider>): …")` and returned to the client as a readable 502; tool errors go back to the model, not the log.
- **Lead integrations:** failed Meta lead fetches are logged as warnings and saved in `lead_integrations.last_error`, shown in Settings → Lead sources.
- **Frontend analytics:** Vercel Web Analytics (page views only) on the deployed site.
- **Health check:** `GET /api/health` → `{"status": "ok"}` (does not touch the database).
- **Audit trail:** business actions are recorded in `audit_logs` and viewable in Settings → Audit log (manager/admin).
- No metrics, tracing, uptime monitoring or error tracking service is set up (beyond what Vercel and Render show by default).

## Target architecture (future phase — plan only)

When the user starts the "Scalability & Production Optimization" phase, the intended direction is:

| Concern | Proposed approach |
|---|---|
| Frontend hosting | Done: Vercel (see "Deployment"). Optional alternative: a container from `frontend/Dockerfile` |
| Backend hosting | Done: Render. Once there are multiple replicas, run `alembic upgrade head` as a release step rather than on every container start |
| Database | Managed PostgreSQL with automated backups; separate DBs per environment |
| CI (GitHub Actions on `akashdabhane/nexa-crm`) | On PR: backend `pytest` with a `postgres` service container; frontend `npm ci`, `tsc --noEmit`, `npm run lint`, `npm run build` |
| CD | Build & push images on merge to `main`; deploy staging, then promote to production |
| Config | Separate staging/preview backends with their own `CORS_ORIGINS`; Supabase Site URL/redirects per environment |
| Observability | Structured JSON logs, error tracking (e.g. Sentry), request metrics/latency, DB slow-query logging, uptime check on `/api/health` |
| Performance & scale | Candidates from the roadmap: Redis caching for dashboard/report aggregates, background jobs for reminders/email, rate limiting (especially `/api/assistant/chat`, which spends paid/limited LLM quota), query/index tuning, horizontal API replicas |
| AI | Paid Gemini tier or a hosted model for production quotas; per-user usage limits |

Each of these is a separate, user-approved change; none should leak into feature work.
