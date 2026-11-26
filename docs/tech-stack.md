# Tech Stack

Versions are taken from `frontend/package.json`, `backend/requirements.txt` and the Dockerfiles. Major versions
matter: several libraries here (Next.js 16, Zod 4, Tailwind 4, React Hook Form resolvers 5, Recharts 3,
SQLAlchemy 2.1) have APIs that differ from older tutorials.

## Runtimes

| Runtime | Version | Where |
|---|---|---|
| Node.js | 22 (`node:22-alpine` in `frontend/Dockerfile`; v22.17 locally); Vercel's runtime in production | Frontend |
| Python | 3.12 (`python:3.12-slim` in `backend/Dockerfile`; venv at `backend/myvenv`); Render in production | Backend |
| PostgreSQL | 18.x local install on port **5432** (primary); `postgres:17-alpine` in `docker-compose.yml` (optional, host port 5433, also the code's default `DATABASE_URL`) | Database |

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
| Toasts | `sonner` | ^2.0.8 |
| Theming | `next-themes` (`ThemeProvider attribute="class"` in `src/app/providers.tsx`, light/dark/system toggle in the top bar; also read by the shadcn Toaster) | ^0.4.6 |
| Analytics | `@vercel/analytics` (`<Analytics />` in `src/app/layout.tsx`; reports only on Vercel) | ^2.0.1 |
| Command/combobox | `cmdk` | ^1.1 |
| Dates | `date-fns`, `react-day-picker` — only inside shadcn `components/ui/calendar.tsx`; app code formats dates with `Intl` in `src/utils/format.ts` | ^4 / ^10 |
| Lint | `eslint` 9 flat config with `eslint-config-next` (core-web-vitals + typescript) | 16.3.6 |
| Icon generation | `sharp` (ships with Next.js; not a direct dependency), used only by `scripts/generate-icons.mjs` (`npm run icons`) | — |

## Backend (`backend/`)

| Concern | Library | Version |
|---|---|---|
| Web framework | `fastapi` (on `starlette` 1.7) | 0.141.1 |
| ASGI server | `uvicorn[standard]` | 0.54.0 |
| Validation / settings | `pydantic`, `pydantic-settings`, `email-validator` | 2.13.5 / 2.15.0 / 2.3.0 |
| ORM | `SQLAlchemy` — **synchronous**, 2.0-style `Mapped[]` models | 2.1.1 |
| Migrations | `alembic` (timestamped file names, env wired to `app.core.config`) | 1.20.0 |
| DB driver | `psycopg[binary]` (psycopg 3) — URLs use `postgresql+psycopg://` | 3.3.6 |
| JWT / secrets | `PyJWT[crypto]` (`PyJWKClient` for JWKS) + `cryptography` (also Fernet encryption of stored Meta Page tokens) | 2.15.0 / 50.0.1 |
| Env loading | `python-dotenv` (via pydantic-settings `.env`) | 1.2.3 |
| AI assistant (`app/services/assistant/`) | `langgraph` (agent graph, `ToolNode`), `langchain` + `langchain-core` (tools, chat models), `langchain-google-genai` (Gemini, pulls in `google-genai`), `langchain-ollama` (+ `ollama` client) | 1.2.18 / 1.4.7 + 1.7.1 / 4.4.2 / 1.1.0 + 0.6.3 |
| Assistant file exports (`app/services/assistant/exports.py`) | `openpyxl` (Excel), `python-docx` (Word), `python-pptx` (PowerPoint; pulls in `pillow`, `XlsxWriter`); `lxml` for both Office libraries | 3.1.5 / 1.2.0 / 1.0.2 |
| Voice input (`app/services/assistant/speech.py`) | `faster-whisper` (OpenAI Whisper on CTranslate2; pulls in `ctranslate2`, `onnxruntime` for the silence filter, `huggingface_hub` for the model download, `tokenizers`, `numpy`). `av` (PyAV) is pinned to 18.1: 19 dropped an argument faster-whisper 1.2.1 still passes | 1.2.1 / av 18.1.0 |
| LLM providers | Google Gemini API (default `gemini-3.5-flash-lite`, fallback `gemini-3.5-flash`) or a local Ollama server (default `qwen3:4b`), chosen by `LLM_PROVIDER` | — |
| Tests | `pytest`, `httpx` (FastAPI `TestClient`) | 9.1.1 / 0.28.1 |

## Architecture summary

- **API style:** REST/JSON under `/api`, OpenAPI docs at `/docs`. Routers per feature in `backend/app/api/routes/`, registered in `backend/app/api/router.py` (`ROUTERS` tuple).
- **Layers:** route (HTTP, deps, response models) → service (business rules: `permissions`, `leads`, `lead_import`, `meta_leads`, `deals`, `pipelines`, `reports`, `audit`, `notifications`, `related`) → SQLAlchemy models. Pydantic schemas in `app/schemas/`.
- **Multi-tenancy:** one database, `organization_id` on every CRM table; `app/db/tenancy.py` scopes each request's SQLAlchemy session to the organization from the `X-Organization-Id` header (session events add the filter and stamp new rows). Roles live on `memberships`.
- **AI assistant:** `POST /api/assistant/chat` → `services/assistant/agent.py` (LangGraph `StateGraph`: `agent` node ⇄ `tools` node until the model answers) → `tools.py` (LangChain `@tool`s that call the existing route functions, so permissions/audit/notifications are shared) → `llm.py` (`build_chat_model`: Gemini with fallback, or Ollama). Stateless: the client sends the full conversation each time. Voice input: the browser records (`MediaRecorder`) → `POST /api/assistant/transcribe` → `speech.py` (Whisper via faster-whisper, CRM names as hints) → text in the chat box.
- **Database:** PostgreSQL; UUID PKs; `created_at`/`updated_at` via `TimestampMixin`; enum-like columns as `VARCHAR` validated by Python `StrEnum`s (`app/models/enums.py`); `ARRAY(String)` for contact tags; `JSONB` for audit details; constraint naming convention in `app/db/base.py`.
- **Auth:** Supabase Auth (hosted) issues JWTs → frontend stores the session in cookies (`@supabase/ssr`) → Axios adds `Authorization: Bearer` and `X-Organization-Id` → FastAPI verifies the token, loads the `Profile` and checks the membership.
- **Frontend state:** server state in TanStack Query (keys: `[resource, "list" | "detail", params]`, plus `"dashboard"`, `"timeline"`, `"board"`, `"notifications"`, `"me"`); list UI state in the URL (`useListState`); the active organization id in `localStorage` (`src/lib/active-organization.ts`); the theme in `next-themes`; form state in React Hook Form; everything else is local `useState` (the assistant's conversation lives in `AssistantSheet` state, which stays mounted in the top bar). **No global client-state library.**
- **Rendering:** route `page.tsx` files are thin server components; feature views are client components (`"use client"`) that fetch through TanStack Query. `src/proxy.ts` (Next 16's replacement for `middleware.ts`) refreshes the session and redirects. The `(app)` layout renders nothing until `OrganizationGate` has a selected, active organization.
- **Hosting:** frontend on Vercel, backend on Render (see `cloud.md`); Dockerfiles and `docker-compose.yml` exist for container runs.

## Commands at a glance

| Task | Command |
|---|---|
| Backend dev server | `cd backend && myvenv\Scripts\activate && uvicorn app.main:app --reload` |
| Frontend dev server | `cd frontend && npm run dev` |
| Migrations | `cd backend && alembic upgrade head` |
| Seed demo data into a separate "Demo Organization" (ask before running on `nexa_crm`, which holds real data) | `cd backend && python -m scripts.seed [--reset \| --clear]` |
| Regenerate app icons | `cd frontend && npm run icons` |
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
