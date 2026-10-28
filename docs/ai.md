# AI Agent Guide

Read this file first. Then read `rules.md` (how to write code here) and `tech-stack.md` (what you may use).
For the frontend, also obey `frontend/AGENTS.md`: **this is Next.js 16 — read the relevant guide in
`frontend/node_modules/next/dist/docs/` before writing Next.js code.** APIs differ from older versions.

## Role declaration (system prompt)

> You are a senior full-stack engineer maintaining **NexaCRM**, a portfolio CRM built with Next.js 16 + FastAPI +
> PostgreSQL + Supabase Auth. Your priorities are, in order: functionality, simplicity, clean code, polish,
> optimization. You make the smallest change that fully solves the task, you match the existing patterns exactly,
> you keep the code explainable in an interview, and you verify your work (tests, typecheck, lint, build, and the
> running app) before reporting it done. You never add infrastructure or dependencies the user did not ask for.

## Domain vocabulary

| Term | Meaning in this codebase |
|---|---|
| **Profile** | App-side user row (`profiles`). `id` = Supabase auth user id (JWT `sub`). Holds `role` and `is_active`. Created just-in-time on the first authenticated request (`app/dependencies/auth.py`). |
| **Role** | `admin`, `manager`, `sales_rep` (`UserRole` in `app/models/enums.py`). "Manager or admin" = `Profile.is_manager_or_admin`. |
| **Owner** | The "assigned user" of a record: `owner_id` on companies, contacts, leads, deals, tasks; the **author** of activities and notes. |
| **Lead** | An unqualified prospect (`leads`) with free-text `company_name`, `source`, `status`, `score` 0–100. |
| **Conversion** | `POST /api/leads/{id}/convert` → Contact + (matched or new) Company + optional Deal, in one transaction (`app/services/leads.py`). Sets lead `status=converted` and `converted_*_id`. |
| **Contact / Company** | A person / an account. A company has many contacts and deals. |
| **Pipeline / Stage** | Ordered `pipeline_stages` with `position`, default `probability`, and `stage_type` ∈ `open`/`won`/`lost`. One **default pipeline** ("Sales Pipeline": New → Contacted → Qualified → Proposal → Negotiation → Won → Lost) is created lazily by `get_default_pipeline()`. |
| **Deal** | An opportunity. `status` mirrors the stage type (`open`/`won`/`lost`); `closed_at` is set when entering won/lost. |
| **Weighted value** | `value × probability / 100`. |
| **Activity** | A logged interaction of type `call`, `meeting` or `email` (`activities`). |
| **Note** | Editable free text (`notes`). Shown in the timeline as the 4th "activity type". |
| **Links** | `contact_id`, `company_id`, `lead_id`, `deal_id` — nullable FKs on activities/notes (and tasks, minus lead). Activities/notes need ≥1 link. |
| **Timeline** | `GET /api/timeline?<one link>=id` — activities + notes merged newest first. A company's timeline includes its contacts' entries. |
| **Task** | To-do with `due_date`, `priority` (low/medium/high/urgent), `status` (pending/in_progress/completed/cancelled), `due_notified` flag. |
| **Notification** | Per-user in-app message: `lead_assigned`, `deal_assigned`, `task_assigned`, `task_due`, `deal_won`, `deal_lost`. |
| **Audit log** | Append-only `audit_logs` row: `action` like `deal.stage_changed`, `entity_type`, `entity_id`, JSONB `details` (`name`, `changes: {field: [old, new]}`, `from`/`to`). |
| **AI assistant** | The chat panel (`features/assistant/assistant-sheet.tsx`) backed by `POST /api/assistant/chat` and the LangGraph agent in `app/services/assistant/`. Turns free text into CRM records. |
| **Tool** | A LangChain `@tool` in `app/services/assistant/tools.py` (`search_records`, `create_lead`, `update_lead`, `create_company`, `create_contact`, `log_activity`, `add_note`, `create_task`). Returns `(content, artifact)`. |
| **SavedRecord** | A tool's artifact: `{type, action, id, label, link_type, link_id}`. Returned to the UI as links and sent back with later messages so the model can refer to them. |
| **LLM provider** | `LLM_PROVIDER` = `gemini` (Google Gemini via `GEMINI_API_KEY`, with `GEMINI_FALLBACK_MODEL`) or `ollama` (local model). |

## Business rules (invariants — do not break)

**Authentication**
- FastAPI verifies Supabase JWTs itself (`app/core/security.py`): RS256/ES256 via the project JWKS, or legacy HS256 via `SUPABASE_JWT_SECRET`; audience must be `authenticated`; `exp` and `sub` required.
- A new user becomes **admin if no admin exists**, otherwise `sales_rep`. Deactivated users get 403.
- FastAPI never implements registration, login, logout, password reset or email verification — those are Supabase's job, done from the frontend.

**Authorization** (`app/services/permissions.py`, `app/dependencies/auth.py`)
- Everyone can **read** all CRM records.
- Reps **edit only records they own**; managers/admins edit any (`ensure_can_edit`).
- Reps' new records are always owned by themselves; only managers/admins may assign or reassign (`owner_for_create`, `check_owner_change`).
- **Delete** of companies/contacts/leads/deals: managers/admins only (`require_manager`). Authors may delete their own activities, notes and tasks.
- Admin only: `PATCH /api/users/{id}`, pipeline create/stage edits. Manager+: audit log, rep-performance report. An admin cannot demote or deactivate themselves.
- The frontend mirrors these rules for UX (`useCurrentUser().canEdit/isManager/isAdmin`), but **the backend is the source of truth**.

**Leads & deals**
- `status=converted` can only be set by the convert endpoint; a converted lead's status is frozen; converting twice → **409**.
- Conversion matches an existing company by case-insensitive name, else creates one (none if the lead has no company); re-links the lead's activities/notes to the new contact.
- Deal stage changes always go through `apply_stage()` (sets `stage_id`, `pipeline_id`, `status`, `probability`, `closed_at`) — in routes via `_move()` in `app/api/routes/deals.py`, which also audits and notifies. A stage must belong to the deal's pipeline (400 otherwise).
- Money is `Numeric(14,2)`, serialized as float; `currency` is a 3-letter uppercase code; there is **no currency conversion** (report totals sum raw values).

**Side effects**
- Audit entries and notifications are added to the **same session** and committed with the change (`app/services/audit.py`, `app/services/notifications.py`). Use `audit.apply_changes()` for updates so only real changes are logged.
- Nobody is notified about their own action. Won/lost notifies the deal owner + all active managers/admins (except the actor).
- "Task due" notifications are generated **lazily** when a user calls `GET /api/notifications` or `/unread-count` (once per task; reset when `due_date` changes). There is no scheduler.

**Lists**
- All list endpoints paginate, search, filter and sort **in SQL**. `sort_by` must be whitelisted in a `SORTABLE` dict. Response shape: `{items, total, page, page_size, pages}`; `page_size` ≤ 100.

**AI assistant** (`app/services/assistant/`)
- Tools **must call the existing route/service functions** with the normal Pydantic schemas, never write models directly, so permissions, validation, audit and notifications stay identical to the UI.
- The DB session and user come from the LangGraph `configurable` config; they're never exposed to the model. Tools run sequentially (`max_concurrency=1`) because they share one session.
- Each successful tool call commits on its own; a failing one is rolled back and its error returned to the model as `{"error": …}` data. Records saved before a later failure are still reported to the user.
- The model can't set `status=converted` (`OpenLeadStatus`), can't link tasks to leads (tasks have no `lead_id`), and has no tools for deals, conversion or deletes.
- The server is stateless: requests carry the whole conversation (1–50 messages, last one from the user, ≤ 8,000 chars each).
- Errors: missing `GEMINI_API_KEY` → **503**; model failure with nothing saved → **502** with a human-readable reason. At most 10 model rounds per message (`MAX_STEPS`).

## What an AI agent MAY do

- Implement features, fix bugs and write tests inside the existing architecture.
- Add backend routes/schemas/services/models following the recipe in `rules.md`, including Alembic migrations (autogenerate, then **review** the file).
- Add shadcn/ui components via `npx shadcn@latest add <name>` (they land in `frontend/src/components/ui/`).
- Run local commands: tests, lint, typecheck, build, dev servers and migrations. Run the seed script only against an empty or test database (see DO NOT).
- Update these context `.md` files when the facts they describe change (see `contributing.md`).

## DO NOT

- **Do not add infrastructure**: no Redis, Celery, RQ, Kafka, message queues, workers, cron services, websockets, Kubernetes or microservices — unless the user explicitly starts the "Scalability & Production Optimization" phase.
- **Do not add dependencies** (npm or pip) without asking. Specifically forbidden: see "Forbidden" in `tech-stack.md` (e.g. zustand/redux, other UI kits, drag-and-drop libraries, async SQLAlchemy, python-jose, passlib).
- **Do not build auth endpoints** (register/login/logout/reset/verify) in FastAPI, and never handle passwords in the backend.
- **Do not use or request the Supabase service-role key**; never put secrets in `NEXT_PUBLIC_*` variables or in code.
- **Do not refactor, rename or restructure** working code that the task doesn't require. No drive-by "cleanups" of shadcn-generated files in `components/ui/`.
- **Do not bypass the permission helpers** or move authorization to the frontend.
- **Do not change the database schema without a migration**, and never edit an already-applied migration — add a new one.
- **Do not load whole tables into the frontend** to filter/sort/paginate client-side.
- **Do not overwrite `.env` files** (`backend/.env`, `frontend/.env`, `frontend/.env.local`) — they contain the user's secrets. Only `*.env.example` files are yours to edit. Never print secret values; mask passwords in any output.
- **Do not commit, push, or rewrite git history unless asked.**
- **Do not use Docker** for local work unless asked — the user runs PostgreSQL 18 locally (port 5432) and the backend via `uvicorn` directly.
- **Do not introduce SQLite** (tests and app rely on PostgreSQL features: `ARRAY`, `JSONB`, `date_trunc`, `FILTER`).
- **Do not run `python -m scripts.seed`** (any mode) against `nexa_crm`: it holds the user's real CRM data, and `--reset`/`--clear` delete it.
- **Do not call a real LLM from tests.** Use the `ScriptedModel` fake in `backend/tests/test_assistant.py`. The Gemini free tier allows only a few requests per day (around 20 for Flash), so do live assistant checks sparingly, and only against the `nexa_crm_test` database.
- **Do not claim something works without running it.** If you couldn't verify (e.g. a signed-in browser flow), say so.

## Working loop

1. Read the relevant route/service/model and the matching frontend `features/<module>/` folder before changing anything.
2. Reuse helpers: `list_params`, `apply_sort`, `paginate`, `get_or_404`, `search_filter`, permission helpers, `audit`, `notifications`; on the frontend `createCrudService`, `createResourceHooks`, `useListState`, `DataTable`, `FormField`, `EntityCombobox`, `RecordTabs`.
3. Write or update backend tests (`backend/tests/`) for any rule or endpoint you touch.
4. Verify: `pytest`, `npx tsc --noEmit`, `npm run lint`, `npm run build`, and exercise the change in the running app.
5. Report plainly what changed, what was verified, and what was not.
