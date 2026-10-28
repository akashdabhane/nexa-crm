# Engineering Rules

These rules describe how code in this repository is actually written. Match them exactly; consistency beats
personal preference.

## Repository layout (do not reorganize)

```
nexa-crm/
├── backend/app/
│   ├── main.py                 # app factory, CORS, global exception handlers
│   ├── core/                   # config.py (settings), security.py (JWT), exceptions.py (HTTP error helpers)
│   ├── db/                     # base.py (Base, UUIDPrimaryKeyMixin, TimestampMixin), session.py (engine, get_db)
│   ├── models/                 # one module per table group; ALL re-exported in models/__init__.py
│   ├── schemas/                # Pydantic models per resource (+ common.py, related.py)
│   ├── services/               # business logic, no HTTP concerns except raising helpers from core/exceptions
│   │   └── assistant/          # agent.py (LangGraph graph, prompt), tools.py (LangChain tools), llm.py (model factory)
│   ├── api/router.py           # ROUTERS tuple → /api
│   ├── api/routes/<feature>.py # one APIRouter per feature
│   ├── dependencies/           # auth.py (get_current_user, require_roles/admin/manager), pagination.py
│   └── utils/query.py          # search_filter, apply_sort, paginate, get_or_404
├── backend/alembic/versions/   # YYYY_MM_DD_HHMM-<rev>_<slug>.py
├── backend/scripts/seed.py     # python -m scripts.seed
├── backend/tests/              # test_<area>.py, fixtures in conftest.py
└── frontend/src/
    ├── app/(auth)/…            # login, signup, forgot-password, reset-password
    ├── app/(app)/<route>/page.tsx   # thin pages; layout.tsx = shell; error.tsx
    ├── app/auth/callback/route.ts
    ├── proxy.ts
    ├── components/{ui,shared,layout}/
    ├── features/<module>/      # views, dialogs, tabs, hooks.ts for one module (assistant/ = chat panel)
    ├── hooks/                  # use-current-user, use-list-state, use-resource, use-mobile
    ├── lib/                    # api-client.ts, supabase/*, utils.ts
    ├── services/<resource>.ts  # typed API functions
    ├── types/index.ts          # all shared TS types + enum const arrays
    └── utils/format.ts         # Intl formatting helpers
```

## Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `apply_stage`, `owner_for_create` |
| Python classes, Pydantic schemas | `PascalCase`; schemas suffixed `Create` / `Update` / `Read` | `DealCreate`, `LeadConvertResult` |
| Enums | `StrEnum` in `app/models/enums.py`, UPPER members, lowercase values | `TaskStatus.IN_PROGRESS = "in_progress"` |
| Tables | plural `snake_case` | `pipeline_stages`, `audit_logs` |
| Audit actions | `<entity>.<past-tense verb>` | `lead.converted`, `deal.stage_changed` |
| API paths | plural kebab/lowercase nouns, actions as sub-resources | `/api/leads/{id}/convert`, `/api/reports/win-loss` |
| Frontend files | `kebab-case.tsx` / `.ts` | `deal-form-dialog.tsx`, `use-list-state.ts` |
| React components | `PascalCase`, named exports (pages use `default`) | `export function DealsView()` |
| Hooks | `use*`, files `use-*.ts` (global) or `hooks.ts` (per feature) | `useMoveDeal`, `dealHooks.useList` |
| Feature files | `<entity>s-view.tsx` (list), `<entity>-detail.tsx`, `<entity>-form-dialog.tsx`, `<entity>-tabs.tsx`, `related-<entities>.tsx` | `features/leads/lead-detail.tsx` |
| TS enum lists | `UPPER_SNAKE` `as const` arrays + derived union types | `LEAD_STATUSES`, `type LeadStatus` |

## Backend patterns

**Adding a resource (recipe):**
1. Model in `app/models/<name>.py` using `UUIDPrimaryKeyMixin, TimestampMixin, Base`; `Mapped[...]` annotations; FKs with explicit `ondelete`; indexes on filter columns; many-to-one relationships `lazy="joined"` (or `selectin` for optional links). Add it to `app/models/__init__.py` and `__all__`.
2. Schemas in `app/schemas/<name>.py`: request bodies extend `InputSchema` (strips strings, turns `""` into `None`); responses extend `ORMSchema`; embed related records as `EntityRef` (`{id, name}`) and owners as `ProfileSummary`.
3. Business logic that is reused or non-trivial goes in `app/services/`.
4. Router in `app/api/routes/<name>.py`: `APIRouter(prefix="/<names>", tags=[...])`; list endpoint uses `Depends(list_params)` + filters + `apply_sort(stmt, params, SORTABLE, default=...)` + `paginate(...)`; `get_or_404`; `ensure_can_edit` / `owner_for_create` / `check_owner_change`; `require_manager` for deletes; `audit.record(...)` / `audit.apply_changes(...)`; notifications where relevant; `db.commit()` once at the end; `status_code=201` for create, `204` for delete.
5. Register the module in `ROUTERS` in `app/api/router.py`.
6. `alembic revision --autogenerate`, review, `alembic upgrade head`.
7. Tests in `backend/tests/test_<area>.py`.

**Other rules**
- Endpoints are **sync `def`** (sync SQLAlchemy). Don't mix in `async def` endpoints that touch the DB.
- Every endpoint except `/api/health` depends on `get_current_user` (or `require_admin` / `require_manager`).
- Validate existence of referenced IDs and raise **400** (`bad_request`) for bad links; **404** (`not_found`) for the path resource; **403** (`forbidden`) for permissions; **409** (`conflict`) for state conflicts; let Pydantic produce **422**. For a failing upstream service (the LLM) use **502** (`bad_gateway`); for a missing configuration **503** (`service_unavailable`).
- Raise the helpers in `app/core/exceptions.py`; never return error dicts manually. Never leak exception details to clients (the global handler logs and returns a generic 500).
- Updates: `payload.model_dump(exclude_unset=True)`; drop `None` for non-nullable columns; apply via `audit.apply_changes` so the audit diff is exact.
- Never build SQL with string formatting; use SQLAlchemy expressions. Sort only by whitelisted columns.
- Datetimes are timezone-aware UTC (`datetime.now(UTC)`, `DateTime(timezone=True)`); dates are `date`. Report date ranges use `DateRange` (inclusive days).
- Type hints on all function signatures; `X | None` style; no `Any` unless unavoidable.
- Logging: use `logging.getLogger("nexa_crm")`; no `print` in app code (the seed script may print).

**Adding an AI assistant tool (recipe)**
1. In `app/services/assistant/tools.py`, write a `@tool(response_format="content_and_artifact")` function. Describe every argument with `Annotated[..., "description"]` (the model reads them) and take `config: RunnableConfig`.
2. Inside, define `action(db, user)` that builds the normal `*Create`/`*Update` schema from `_given(...)` (drops empty args) and calls the **existing route function** (e.g. `tasks.create_task(payload, user, db)`). Return `(json-able dict for the model, SavedRecord | None)`; build the record with `_saved(...)`.
3. `return _run(config, action)`. It supplies the session and user and turns `ValueError`/`HTTPException` into `{"error": …}` for the model.
4. Add it to `TOOLS`; extend `SavedRecord.type` in `app/schemas/assistant.py`, `AssistantRecord` in `frontend/src/types/index.ts` and `RECORD_ICONS` in `assistant-sheet.tsx` if it saves a new kind of record; mention it in `SYSTEM_PROMPT` if the model needs guidance on when to use it.
5. Test it in `tests/test_assistant.py` with `ScriptedModel` (tool call → assert DB rows, audit entry and the returned `records`).
- Model access only goes through `build_chat_model()` in `llm.py`; keep provider-specific code there.

## Frontend patterns

- **Data access:** add API calls to `src/services/<resource>.ts` (use `createCrudService<T, TInput>(path)` for standard REST), then hooks in `features/<module>/hooks.ts` via `createResourceHooks(key, service, { label, related })`. Mutations toast success/error and invalidate related keys automatically. Only use raw `useQuery`/`useMutation` for non-CRUD endpoints (reports, board, notifications, assistant chat).
- **Never call Axios from components** directly; never use `fetch` for the API.
- **List pages:** `useListState({ filters, defaultSort, defaultOrder })` → pass `list.params` to `useList`. Use `setFilters` (not two `setFilter` calls) when changing several filters at once.
- **Pages:** `app/(app)/<route>/page.tsx` exports `metadata` and renders a feature view. Wrap views that use `useSearchParams` in `<Suspense>`. Dynamic routes: `async function Page({ params }: PageProps<"/deals/[id]">) { const { id } = await params; }`.
- **Forms:** React Hook Form + `zodResolver(schema)`; keep form values as strings and convert on submit; `values:` (not `defaultValues`) when the form edits a loaded record; `Controller` for Select/Combobox/Checkbox; `useWatch` (not `watch`, which breaks React Compiler memoization); submit with `try { await mutation.mutateAsync(...) } catch {}` — the hook already shows the error toast.
- **Permissions in UI:** `useCurrentUser()` → `canEdit(record)`, `isManager`, `isAdmin`. Hide what the user can't do.
- **Next.js 16 specifics:** `proxy.ts` not `middleware.ts`; `error.tsx` receives `retry`; `cookies()`/`params` are async; global `PageProps`/`LayoutProps` types. Check `node_modules/next/dist/docs/` when unsure.
- **Styling:** Tailwind utilities + tokens; compose `className` with `cn()` from `@/lib/utils`; use shadcn variants (`variant`, `size`) before custom classes. See `design.md`.
- **Typing:** TypeScript `strict`; no `any` (use `unknown` + narrowing); shared API types live in `src/types/index.ts` and must mirror the Pydantic `Read` schemas; enum values come from the `as const` arrays.
- **Errors:** show `ErrorState` for failed queries, `EmptyState` for no data, skeletons while loading; human messages via `getErrorMessage(error)`.

## How to reason through a change

1. **Restate the goal** and which roles/permissions it touches. If requirements are ambiguous in a way that changes the data model or permissions, ask.
2. **Find the existing pattern.** Search for the closest existing feature (e.g. a new resource → copy the shape of `tasks`/`notes`; a new report → `app/services/reports.py` + `features/reports/reports-view.tsx`). Check `components/shared/` and the helpers listed above before creating anything new.
3. **Design the data first:** model/migration → schemas → service rules → endpoint → types → service fn → hooks → UI.
4. **Write/extend the backend test first** for new rules (permission, validation, side effects), watch it fail, then implement.
5. **Keep side effects consistent:** audit entry, notifications, TanStack invalidations (`related` keys), dashboard/timeline refresh.
6. **Verify** with the checklist in `production.md`, including the running UI.
7. **Update docs** (`README.md`, `docs/ARCHITECTURE.md`, these context files) when you change behavior, endpoints, env vars or dependencies.

## Things that look wrong but are intentional

- `Deal.status` duplicates the stage type — deliberate denormalization for simple reporting.
- `Contact.name` property exists only so contacts fit the generic `EntityRef` schema.
- Notes use `owner_id` for the author so the same `ensure_can_edit` rule applies.
- `GET /api/pipelines` and `/deals/board` may create the default pipeline (lazy provisioning).
- `GET /api/notifications*` may create `task_due` notifications (lazy reminders instead of a scheduler).
- Assistant tools import and call route functions (`app.api.routes.leads.create_lead`, …) from a service. That's deliberate: one code path for UI and chat.
- Each assistant tool commits on its own, so a chat that fails halfway keeps what it already saved (and says so).
- `useAssistantChat` calls `queryClient.invalidateQueries()` with no key after a chat that saved anything; the assistant can touch any list, detail or timeline.
- The assistant's conversation isn't persisted anywhere; "New chat" or a page reload clears it.
- shadcn components in `components/ui/` import `cn` from the `cn` package; app code imports it from `@/lib/utils` (which re-exports the same function).
