# Contributing

How humans and AI agents keep the code **and** its context documents correct. All context files live in `docs/`;
`README.md` is at the repository root.

## The context files

| File | Owns | Update when… |
|---|---|---|
| `purpose.md` | Mission, personas, scope | Scope changes, a module is added/removed, a new persona or role appears |
| `ai.md` | Agent role, domain vocabulary, business rules, DO/DO NOT | Any business rule, permission, status/enum value, or domain concept changes |
| `tech-stack.md` | Versions, architecture summary, forbidden packages | A dependency is added/removed/upgraded a major version; architecture changes |
| `design.md` | Tokens, typography, patterns, shared components, a11y | `globals.css` tokens, status tones, shared components or page patterns change |
| `production.md` | Env vars, build, tests, lint, migrations, checklist | New env var, script, test tooling, build config or dependency-file convention |
| `cloud.md` | Deployment, integrations, secrets, logging | Any external service, deployment, CI/CD, logging/monitoring change |
| `rules.md` | Code style, structure, patterns, reasoning steps | A new convention or shared abstraction is introduced |
| `contributing.md` | This process, git workflow | The workflow changes |
| `README.md` | User-facing overview, setup, API summary | Features, setup steps or endpoints change |
| `docs/ARCHITECTURE.md` | Detailed schema, ER diagram, design decisions, AI assistant flow | Schema, major design decisions or the assistant's graph/tools change |
| `docs/USER_GUIDE.md` | How end users set up and use each feature | A user-visible feature or workflow changes |

**Rules for maintaining them**
1. Update the docs **in the same change** as the code that makes them stale — never "later".
2. State facts that are true of the code now. Mark plans explicitly as plans ("future phase", "proposed").
3. Be specific: real paths, real package names, real commands. No generic placeholders.
4. Don't duplicate large sections across files; link to the owning file instead.
5. If you find a doc that contradicts the code, fix the doc (or flag it) — the code wins unless the doc describes an agreed rule the code violates, in which case fix the code.
6. AI agents: before finishing a task, re-read the table above and list which context files you updated (or why none needed updating).

## Git workflow

- **Remote:** `origin` → `https://github.com/akashdabhane/nexa-crm.git`. **Default branch:** `main`.
- **Branches:** work on short-lived branches off `main`, merged via pull request:
  `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`, `refactor/<topic>`, `test/<topic>` (e.g. `feat/contact-company-filter`).
- Keep `main` green: backend tests, typecheck, lint and build pass before merging (see `production.md`).
- Rebase or merge `main` into your branch before opening/updating a PR; resolve conflicts locally.
- **AI agents never commit, push, create branches or open PRs unless the user asks**, and never force-push or rewrite history on `main`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) going forward (the first two commits predate this):

```
<type>(<scope>): <imperative summary, ≤ 72 chars>

<optional body: what and why, wrapped at ~72 chars>
```

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `perf`, `style`.
- **Scopes:** `backend`, `frontend`, `auth`, `contacts`, `companies`, `leads`, `deals`, `pipeline`, `activities`, `tasks`, `reports`, `notifications`, `audit`, `assistant`, `db`, `docker`, `docs`.
- Examples:
  - `feat(leads): carry lead notes over on conversion`
  - `fix(backend): add connect_timeout so DB outages fail fast`
  - `feat(assistant): add a create_task tool`
  - `docs: update tech-stack for recharts 3`
- One logical change per commit; migrations are committed together with the model change that needs them.
- Commits created by an AI agent end with the attribution line the environment specifies (e.g. `Co-Authored-By: …`).

## Pull request checklist

- [ ] Description: what changed, why, how it was verified (commands + manual steps).
- [ ] `cd backend && pytest` passes; new behavior has tests.
- [ ] `cd frontend && npx tsc --noEmit && npm run lint && npm run build` pass.
- [ ] Alembic migration included and reviewed (if models changed).
- [ ] No `.env`, credentials, `myvenv/`, `node_modules/`, `.next/`, `__pycache__/` in the diff.
- [ ] Context files and README updated where relevant.
- [ ] Screenshots for visible UI changes.

## Never commit

`backend/.env`, `frontend/.env`, `frontend/.env.local`, any root `.env`, the Supabase JWT secret, the Gemini API key,
database passwords, `backend/myvenv/`, `frontend/node_modules/`, `frontend/.next/`, `__pycache__/`, `.pytest_cache/`.
All are covered by the `.gitignore` files — don't weaken them.
