# NexaCRM User Guide

How to set NexaCRM up for your own business, enter your data, and use every feature.

---

## 1. Before you start

Start both servers (from the project root):

```bash
cd backend && myvenv\Scripts\activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Open **http://localhost:3000**.

The **AI Assistant** also needs a model configured in `backend/.env`: a Google Gemini key in `GEMINI_API_KEY`, or
`LLM_PROVIDER=ollama` with a local Ollama model (see the README). Everything else works without it.

### Accounts and roles

Log in with your Supabase account, or create one at **Sign up** (if email confirmation is on in your Supabase
project, click the link in the email before logging in). The first account ever to sign in became **Admin**; every new account
starts as **Sales Rep**.

| | Admin | Manager | Sales Rep |
|---|:-:|:-:|:-:|
| See all records | ✅ | ✅ | ✅ |
| Create records | ✅ | ✅ | ✅ (owned by themselves) |
| Edit records | any | any | only their own |
| Assign records to someone else, delete records | ✅ | ✅ | ❌ (can delete their own activities, notes, tasks) |
| Sales rep performance report, Audit log | ✅ | ✅ | ❌ |
| Change user roles, edit pipeline stages | ✅ | ❌ | ❌ |

**To change someone's role:** log in as an Admin → **Settings → Users & roles** → pick the role.
Team members must log in once before they appear in this list.

### Starting from an empty CRM

The demo data has been removed. To clear it again in future (for example after re-running the seed):

```bash
cd backend && python -m scripts.seed --clear
```

This keeps real accounts, their roles and your pipeline stages. **Don't run `python -m scripts.seed`
again** unless you want the demo data back — it only runs on an empty CRM, and `--reset` wipes your data.

---

## 2. Recommended setup order

Records link to each other, so entering them in this order means the dropdowns are already filled when
you need them:

1. **Settings → Pipeline** — rename the deal stages to match your sales process (Admin).
2. **Invite your team** — have them sign up, then set their roles (Admin).
3. **Companies** — the organisations you sell to.
4. **Contacts** — people, linked to their company.
5. **Leads** — prospects who aren't qualified yet.
6. **Deals** — real opportunities with a value.
7. Day to day: **Activities, Notes, Tasks** on those records.

Data is entered through the forms in the app, or by describing it to the **AI Assistant** (there is no CSV
import yet). The API at http://localhost:8000/docs accepts the same data if you ever want to script a bulk import.

---

## 3. Features

### Settings

- **Profile** (everyone) — change your display name.
- **Users & roles** (Admin) — set each user's role, or deactivate someone who has left
  (they keep their records but can no longer use the app).
- **Pipeline** (Admin) — rename each stage and set its **default probability** (the % chance a deal at that
  stage closes). Stages are Open, Won or Lost; the seven default stages are
  New → Contacted → Qualified → Proposal → Negotiation → Won / Lost.
- **Audit log** (Admin, Manager) — who created, changed (field by field), converted, moved or deleted
  what, and when.

### Companies

**Companies → New company.** Only *Name* is required; you can also add industry, website, email, phone,
address, city, country, employee count and owner.

- The list can be searched, filtered by industry and owner, sorted by column, and paged.
- A company's page shows its details plus tabs: **Timeline** (activity for the company *and* its
  contacts), **Contacts**, **Deals**, **Tasks**, **Notes**, and its open pipeline value.

### Contacts

**Contacts → New contact.** Only *First name* is required. Link the contact to a **Company**, set a
**Status** (Active, Customer, Inactive) and add **Tags**, separated by commas (e.g.
`decision-maker, vip`).

- Search by name, email, phone or job title; filter by status, tag or owner.
- The contact page has **Timeline**, **Deals**, **Tasks** and **Notes** tabs.

### Leads

A lead is a prospect you haven't qualified yet — someone from a web form, referral, event, etc.

**Leads → New lead.** *Name* is required. Also set email, phone, company name, **Source** (Website,
Referral, Advertisement, Social media, Email, Cold call, Other), **Status** and a **Score** from 0–100
(how promising the lead is — your own judgement).

The list filters by status, source and owner. Work a lead by moving its status: **New → Contacted → Qualified** (or **Unqualified** if it's a dead end).
Log calls and notes on the lead as you go.

**Converting a lead** (button on the lead's page) — when a lead becomes a real opportunity:

- A **Contact** is created from the lead's name, email and phone.
- The lead's company name is matched to an existing **Company** (case-insensitive), or a new one is
  created. You can also pick a company yourself.
- Optionally a **Deal** is created (name, value, expected close date).
- All the lead's activities and notes move to the new contact, so no history is lost.
- The lead is marked **Converted** with links to everything it became. A lead can only be converted once.

### Deals

**Deals → New deal.** *Name* is required. Set the **Value** and currency, **Stage** (first stage if left
empty), **Company**, **Primary contact**, **Expected close date**, owner and description.

- **Probability** comes from the stage's default but can be overridden per deal. The **weighted value**
  (value × probability) is what the dashboard's "Weighted pipeline" adds up.
- On a deal's page, click a stage in the **stage path** to move it. Moving to **Won** or **Lost** closes
  the deal, records the close date and notifies the deal's owner.
- The Deals list filters by stage, status (open/won/lost) and owner.

### Pipeline (Kanban board)

**Pipeline** shows every open deal as a card in its stage column, with the column's deal count and
total value. **Drag a card** to another column to move it, or use the card's **Move to** menu
(handy on touch screens). Dropping on Won/Lost closes the deal.

### Activities

An activity is something that happened: a **Call**, **Meeting** or **Email**.

**Log activity** (on the Activities page, or on any contact, company, lead or deal page): choose the
type, enter a subject, when it happened, duration and notes, and link it to the contact, company and/or
deal. One activity can appear on several timelines — e.g. a call shows on both the contact and the deal.

The **Activities** page is a chronological feed for the whole team, filterable by type, owner and date.

### Notes

Free-text notes on any contact, company, lead or deal (**Notes** tab). Only the author can edit their
note. Notes also appear in the record's **Timeline**.

### Tasks

Things to do: *Title* is required, plus description, **Due date**, **Priority** (Low, Medium, High,
Urgent), **Status** (Pending, In progress, Completed, Cancelled), assignee, and links to a contact,
company or deal.

- **Tasks** page views: **Open**, **Overdue**, **Completed**, **All** — and **My tasks / Team**.
- Tick a task to complete it. Overdue tasks are highlighted.
- Create tasks from a record's **Tasks** tab to link them automatically.

### Notifications

The **bell** in the top bar shows unread notifications (checked every 60 seconds). You're notified when:

- someone else assigns you a lead, deal or task;
- one of your tasks is due tomorrow, due today, or overdue;
- one of your deals is marked won or lost by someone else.

You aren't notified about your own actions. Click a notification to open the record; use **Mark all as
read** on the Notifications page.

### Dashboard

Your home page once data exists: KPI tiles (contacts, companies, leads, active/won/lost deals, pipeline
and weighted value, win rate, lead conversion), pipeline by stage, monthly revenue, recent activity,
**your upcoming tasks**, and lead sources. Each tile links to the matching list.

### Reports

Pick a **date range** at the top, then see:

- **Lead conversion** — rate and average days to convert.
- **Sales pipeline** — open deals per stage, total vs weighted value.
- **Revenue** — value of deals won per month.
- **Won vs lost** — closed deals per month and win rate.
- **Lead source performance** — which sources bring leads that convert.
- **Sales rep performance** (Admin, Manager) — revenue, wins, losses, win rate, open pipeline,
  leads converted and activities per rep.

Reports are only as good as the data: keep deal stages, close dates and lead sources up to date.

### AI Assistant

Click **AI Assistant** in the top bar (on any page) to open the chat panel. Write what happened in your own words,
for example:

> Cold-called Priya Shah, CTO at Brightwave. She's interested in a demo next week.

The assistant will:

- **look for existing records first**, so it reuses a lead, contact or company instead of creating a duplicate;
- create a **lead** for a new prospect (with source, company name and a score), or a **contact/company** when you
  say it's an existing relationship;
- **log the call, email or meeting** on that record, with what was discussed;
- turn promised follow-ups into **tasks** (with due dates like "next Tuesday" worked out for you);
- save background such as budget or needs as a **note**;
- update a lead's **status and score** when your story implies it (e.g. Contacted, Qualified).

Each reply lists what was saved as links; click one to open the record. Click a suggestion to start, press
**Enter** to send (**Shift+Enter** for a new line), and **New chat** to start over. The conversation is kept while
you move between pages, but not after a page reload.

Good to know:

- It can't create deals, convert leads, or delete anything. Use the normal pages for those.
- It follows your permissions: a Sales Rep can't change a teammate's lead through chat either. Everything it saves
  shows up in the audit log and sends the usual notifications.
- It won't make up names or contact details. If something is missing, it asks.
- If the model is busy or the free daily quota is used up, you'll see a message saying so; anything already saved
  stays saved.

---

## 4. A typical day

1. Check the **bell** and **Dashboard → upcoming tasks**.
2. New enquiry → **New lead** (with source and score).
3. After calling them → **Log activity** on the lead, set status to Contacted/Qualified. (Or tell the **AI
   Assistant** about the call, and it does steps 2–3 and creates the follow-up task for you.)
4. Ready to buy → **Convert** the lead, creating the deal.
5. Move the deal across the **Pipeline** as it progresses; add **Tasks** for next steps and **Notes** for
   context.
6. Close it as **Won** or **Lost**.
7. Weekly: review **Reports**; managers check rep performance and the audit log.
