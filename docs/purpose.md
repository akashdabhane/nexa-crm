# Purpose

> Part of the NexaCRM context set in `docs/`: `purpose.md` · `ai.md` · `tech-stack.md` · `design.md` ·
> `production.md` · `cloud.md` · `rules.md` · `contributing.md`. Deeper design detail lives in
> `docs/ARCHITECTURE.md`; end-user instructions in `docs/USER_GUIDE.md`.

## Mission

NexaCRM is a **complete, working, understandable CRM** for small sales teams, inspired by the core of HubSpot.
It is a portfolio project: it must run locally, be explainable end to end in an interview, and look like a
modern SaaS product.

The guiding priority, in order, is:

**FUNCTIONALITY > SIMPLICITY > CLEAN CODE > POLISH > ADVANCED OPTIMIZATION**

Scalability work (Redis, background workers, queues, microservices, Kubernetes, caching, CI/CD, cloud deployment)
is intentionally deferred to a separate, future **"Scalability & Production Optimization"** phase. It must not
complicate the core application.

## Core objectives

1. Manage the full sales cycle in one place: **Lead → (convert) → Contact + Company + Deal → pipeline stages → Won/Lost**.
2. Give each rep a clear daily picture: their tasks, recent activity, and pipeline.
3. Give managers visibility: dashboards, reports (conversion, pipeline, revenue, win/loss, rep performance, lead sources) and an audit log.
4. Make data entry nearly effortless: reps describe their day in plain language and the **AI assistant** records it.
5. Keep the architecture small enough that every request path can be traced by reading the code.

## Value proposition

- **One source of truth** for contacts, companies, leads and deals, with every call, meeting, email, note and task attached to the records it concerns.
- **One-click lead conversion** that creates or links the company, creates the contact, optionally opens a deal, and carries the lead's history across.
- **Visual pipeline**: a drag-and-drop Kanban board where moving a card updates status, probability and close date, notifies stakeholders and writes an audit entry.
- **Simple, predictable permissions**: everyone sees the book of business; reps change only what they own.
- **AI assistant**: "Cold-called Priya at Brightwave, she wants a demo next week" becomes a lead, a logged call and a
  follow-up task, created through the same rules, permissions and audit trail as the forms.

## Target users (personas)

| Persona | Role in app | Needs |
|---|---|---|
| **Riley, Sales Representative** | `sales_rep` | Log activities fast (forms or the AI assistant), see "My tasks" and overdue follow-ups, move own deals through the pipeline, convert qualified leads. Must not be able to change or delete teammates' records. |
| **Max, Sales Manager** | `manager` | See the whole team's pipeline and performance, reassign records, clean up (delete) bad data, review the audit log. |
| **Ada, Admin / Owner** | `admin` | Everything a manager can do, plus manage users/roles and pipeline stage names/probabilities. The first person to sign in (while no admin exists) becomes Admin. |
| **Developer / interviewer** | — | Read the code and understand auth, data model, business rules and trade-offs quickly. |

## Problems solved

| Problem | How NexaCRM solves it |
|---|---|
| Customer info scattered across spreadsheets and inboxes | Central contacts/companies with tags, owners, search and filters |
| Leads fall through the cracks | Lead statuses, sources and 0–100 scores; conversion workflow; lead-source performance report |
| No visibility into the pipeline | Kanban board, weighted pipeline value, pipeline/revenue/win-loss reports |
| Forgotten follow-ups | Tasks with due dates and priorities, overdue view, lazy "task due" notifications |
| "Who changed this?" | Audit log with field-level diffs, stage transitions and conversions |
| Unclear ownership | `owner_id` on every main record, assignment notifications, role-based edit rights |
| Reps skip logging because forms are tedious | AI assistant chat panel: free-text in, structured leads/activities/notes/tasks out, with links to what was saved |

## Scope boundaries

In scope: the modules listed above, Supabase-based authentication, a single default sales pipeline in the UI,
in-app notifications, the AI assistant (Google Gemini or a local Ollama model) for creating/updating leads,
contacts, companies, activities, notes and tasks, local development (plain local PostgreSQL or Docker Compose).

Out of scope for now: email/calendar sync, multi-currency conversion, custom fields, CSV import/export,
multiple pipelines in the UI, realtime push, background jobs, AI features beyond the chat assistant (deals, lead
conversion or reports through chat; saved chat history; streaming replies), and anything else in the deferred
scalability phase.
