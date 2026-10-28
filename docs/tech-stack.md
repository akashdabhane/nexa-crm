# Tech Stack

Versions are taken from `frontend/package.json`, `backend/requirements.txt` and the Dockerfiles. Major versions
matter: several libraries here (Next.js 16, Zod 4, Tailwind 4, React Hook Form resolvers 5, Recharts 3,
SQLAlchemy 2.1) have APIs that differ from older tutorials.

## Runtimes

| Runtime | Version | Where |
|---|---|---|
| Node.js | 22 (`node:22-alpine` in `frontend/Dockerfile`; v22.17 locally) | Frontend |
| Python | 3.12 (`python:3.12-slim` in `backend/Dockerfile`; venv at `backend/myvenv`) | Backend |
| PostgreSQL | 18.x local install on port **5432** (primary); `postgres:17-alpine` in `docker-compose.yml` (optional, host port 5433) | Database |

## Frontend (`frontend/`)

| Concern | Library | Version |
|---|---|---|
| Framework | `next` (App Router, Turbopack dev, `output: "standalone"`) | 16.3.6 |
| UI runtime | `react`, `react-dom` | 19.2.8 |
| Language | `typescript` (`strict: true`, path alias `@/* → src/*`) | ^5 |
| Styling | `tailwindcss` + `@tailwindcss/postcss`, `tw-animate-css` | ^4 |
| Component system | shadcn/ui (`shadcn` CLI package, style **`radix-nova`**, base Radix via `radix-ui`), `class-variance-authority` | shadcn ^4.21, radix-ui ^1.6.7 |
| Class merging | `cn` (shadcn's clsx + tailwind-merge replacement); re-exported by `src/lib/utils.ts` | ^0.4.0 |
| Icons | `lucide-react` | ^1.48 |
| Server state | `@tanstack/react-query` | ^5.104 |
| HTTP | `axios` (single instance in `src/lib/api-client.ts`) | ^1.20 |
| Forms | `react-hook-form` + `@hookform/resolvers` (zodResolver) | ^7.89 / ^5.9 |
| Validation | `zod` (v4 API: `z.email()`, `{ error: "…" }`) | ^4.6 |
| Auth client | `@supabase/supabase-js` + `@supabase/ssr` (cookie sessions) | ^2.117 / ^0.12.7 |
| Charts | `recharts` via shadcn `chart.tsx` | ^3.8 |
| Toasts | `sonner` (+ `next-themes`, used only by the shadcn Toaster) | ^2.0.8 |
| Command/combobox | `cmdk` | ^1.1 |
| Dates | `date-fns`, `react-day-picker` — only inside shadcn `components/ui/calendar.tsx`; app code formats dates with `Intl` in `src/utils/format.ts` | ^4 / ^10 |
| Lint | `eslint` 9 flat config with `eslint-config-next` (core-web-vitals + typescript) | 16.3.6 |

## Backend (`backend/`)

| Concern | Library | Version |
|---|---|---|
| Web framework | `fastapi` (on `starlette` 1.7) | 0.141.1 |
| ASGI server | `uvicorn[standard]` | 0.54.0 |
| Validation / settings | `pydantic`, `pydantic-settings`, `email-validator` | 2.13.5 / 2.15.0 / 2.3.0 |
| ORM | `SQLAlchemy` — **synchronous**, 2.0-style `Mapped[]` models | 2.1.1 |
| Migrations | `alembic` (timestamped file names, env wired to `app.core.config`) | 1.20.0 |
| DB driver | `psycopg[binary]` (psycopg 3) — URLs use `postgresql+psycopg://` | 3.3.6 |
| JWT | `PyJWT[crypto]` (`PyJWKClient` for JWKS) + `cryptography` | 2.15.0 / 50.0.1 |
| Env loading | `python-dotenv` (via pydantic-settings `.env`) | 1.2.3 |
| AI assistant (`app/services/assistant/`) | `langgraph` (agent graph, `ToolNode`), `langchain` + `langchain-core` (tools, chat models), `langchain-google-genai` (Gemini, pulls in `google-genai`), `langchain-ollama` (+ `ollama` client) | 1.2.18 / 1.4.7 + 1.7.1 / 4.4.2 / 1.1.0 + 0.6.3 |
| LLM providers | Google Gemini API (default `gemini-3.5-flash-lite`, fallback `gemini-3.5-flash`) or a local Ollama server (default `qwen3:4b`), chosen by `LLM_PROVIDER` | — |
| Tests | `pytest`, `httpx` (FastAPI `TestClient`) | 9.1.1 / 0.28.1 |

## Architecture summary

- **API style:** REST/JSON under `/api`, OpenAPI docs at `/docs`. Routers per feature in `backend/app/api/routes/`, registered in `backend/app/api/router.py` (`ROUTERS` tuple).
- **Layers:** route (HTTP, deps, response models) → service (business rules: `permissions`, `leads`, `deals`, `pipelines`, `reports`, `audit`, `notifications`, `related`) → SQLAlchemy models. Pydantic schemas in `app/schemas/`.
- **AI assistant:** `POST /api/assistant/chat` → `services/assistant/agent.py` (LangGraph `StateGraph`: `agent` node ⇄ `tools` node until the model answers) → `tools.py` (LangChain `@tool`s that call the existing route functions, so permissions/audit/notifications are shared) → `llm.py` (`build_chat_model`: Gemini with fallback, or Ollama). Stateless: the client sends the full conversation each time.
- **Database:** PostgreSQL; UUID PKs; `created_at`/`updated_at` via `TimestampMixin`; enum-like columns as `VARCHAR` validated by Python `StrEnum`s (`app/models/enums.py`); `ARRAY(String)` for contact tags; `JSONB` for audit details; constraint naming convention in `app/db/base.py`.
- **Auth:** Supabase Auth (hosted) issues JWTs → frontend stores the session in cookies (`@supabase/ssr`) → Axios adds `Authorization: Bearer` → FastAPI verifies and loads the `Profile`.
- **Frontend state:** server state in TanStack Query (keys: `[resource, "list" | "detail", params]`, plus `"dashboard"`, `"timeline"`, `"board"`, `"notifications"`, `"me"`); list UI state in the URL (`useListState`); form state in React Hook Form; everything else is local `useState` (the assistant's conversation lives in `AssistantSheet` state, which stays mounted in the top bar). **No global client-state library.**
- **Rendering:** route `page.tsx` files are thin server components; feature views are client components (`"use client"`) that fetch through TanStack Query. `src/proxy.ts` (Next 16's replacement for `middleware.ts`) refreshes the session and redirects.

## Commands at a glance

| Task | Command |
|---|---|
| Backend dev server | `cd backend && myvenv\Scripts\activate && uvicorn app.main:app --reload` |
| Frontend dev server | `cd frontend && npm run dev` |
| Migrations | `cd backend && alembic upgrade head` |
| Seed demo data (empty databases only; `nexa_crm` holds real data) | `cd backend && python -m scripts.seed [--reset \| --clear]` |
| Backend tests | `cd backend && pytest` |
| Local model for the assistant (optional) | `ollama pull qwen3:4b`, then `LLM_PROVIDER=ollama` in `backend/.env` |
| Frontend checks | `cd frontend && npm run lint && npx tsc --noEmit && npm run build` |

## Forbidden / deprecated

Do not add these (ask the user first if you believe one is truly needed):

| Don't use | Use instead / reason |
|---|---|
| `zustand`, `redux`, `jotai`, `recoil`, MobX | TanStack Query + URL state + `useState` (explicit project decision) |
| `supabase` npm package (the CLI) as an app dependency | `@supabase/supabase-js` + `@supabase/ssr` |
| `@supabase/auth-helpers-nextjs` (deprecated) | `@supabase/ssr` |
| `middleware.ts` | `src/proxy.ts` (Next.js 16 convention) |
| `reset` prop in `error.tsx` | `retry` (Next.js 16) |
| `clsx` / `tailwind-merge` directly | `cn` from `@/lib/utils` |
| MUI, Chakra, Ant Design, Mantine, Bootstrap, styled-components, Emotion | shadcn/ui + Tailwind |
| `@dnd-kit/*`, `react-beautiful-dnd` | Native HTML5 drag-and-drop in `components/shared/kanban-board.tsx` |
| `moment`, `dayjs` | `Intl` helpers in `src/utils/format.ts` |
| `fetch` wrappers / `ky` / SWR for API calls | The shared Axios instance + TanStack Query |
| Tailwind v3 config (`tailwind.config.js`) | Tailwind v4 CSS-first config in `src/app/globals.css` |
| Async SQLAlchemy, `asyncpg`, `databases`, SQLModel, Tortoise | Sync SQLAlchemy 2 + psycopg 3 |
| `psycopg2` | `psycopg[binary]` 3 |
| `python-jose` | `PyJWT[crypto]` |
| `passlib`, `bcrypt`, custom password/JWT issuing | Supabase Auth (backend never handles passwords) |
| Celery, Redis, RQ, Kafka, APScheduler, Dramatiq | Deferred to the scalability phase |
| SQLite (app or tests) | PostgreSQL (`nexa_crm`, `nexa_crm_test`) |
| Supabase service-role key | Not needed anywhere |
| Calling LLM SDKs (`google-genai`, `ollama`, `openai`, …) directly from app code | The LangChain chat models built in `app/services/assistant/llm.py`; ask before adding another provider |
