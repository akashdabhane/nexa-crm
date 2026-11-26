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
project, click the link in the email before logging in). After logging in you land on **Your organizations**: click an
organization to open it. Each organization's contacts, companies, leads and deals are visible only to its members.

- **New here?** Ask an Admin of your team's organization to invite your email address. The invitation shows up on
  Your organizations; click **Accept & open**. Or click **Create organization** to start your own (you become its Admin).
- **Admins** invite people in **Settings → Users & roles**, choosing their role. Turning a member's *Active* switch off
  blocks their access to the organization; removing them takes them out (their records stay).
- Roles apply per organization: you can be Admin in one and Sales Rep in another. Switch organizations from the box
  at the top of the sidebar (or **All organizations** in it to go back to the list).
- Invitations aren't emailed: tell the person to sign in (or sign up) with the invited address and open Your
  organizations. An invitation is valid for 14 days; inviting the same address again renews it.

| | Admin | Manager | Sales Rep |
|---|:-:|:-:|:-:|
| See all of the organization's records | ✅ | ✅ | ✅ |
| Create records | ✅ | ✅ | ✅ (owned by themselves) |
| Edit records | any | any | only their own |
| Assign records to someone else, delete records | ✅ | ✅ | ❌ (can delete their own activities, notes, tasks) |
| Sales rep performance report, Audit log | ✅ | ✅ | ❌ |
| Invite and manage members, rename the organization, edit pipeline stages, connect lead sources | ✅ | ❌ | ❌ |

**To change someone's role:** log in as an Admin → **Settings → Users & roles** → pick the role in the members
table. People appear there once they've accepted an invitation. You can't change your own role or remove yourself,
and every organization keeps at least one active Admin.

### Starting from an empty CRM

A new organization starts empty, with the default pipeline already set up. Each organization's data is separate, so
nothing you enter is visible in another organization.

Demo data (`python -m scripts.seed`) goes into its own **Demo Organization** with placeholder team members; it never
touches your organizations. `python -m scripts.seed --clear` deletes that demo organization again. Since the seed still
writes to your real database, only run it if you actually want the demo organization.

---

## 2. Recommended setup order

Records link to each other, so entering them in this order means the dropdowns are already filled when
you need them:

1. **Your organizations → Create organization** — name it after your business (you become its Admin). Rename it
   later in **Settings → Organization**.
2. **Settings → Pipeline** — rename the deal stages to match your sales process (Admin).
3. **Settings → Users & roles → Invite people** — enter each teammate's email and role (Admin). They accept on
   their Your organizations page.
4. **Settings → Lead sources** (optional) — connect Facebook/Instagram Lead Ads or a webhook (Admin).
5. **Companies** — the organisations you sell to.
6. **Contacts** — people, linked to their company.
7. **Leads** — prospects who aren't qualified yet.
8. **Deals** — real opportunities with a value.
9. Day to day: **Activities, Notes, Tasks** on those records.

Data is entered through the forms in the app, by describing it to the **AI Assistant**, or — for leads only — with
**Leads → Import** (CSV) and the lead sources above. There is no CSV import for contacts, companies or deals; the API
at http://localhost:8000/docs accepts the same data if you ever want to script one (send the `X-Organization-Id`
header).

---

## 3. Features

### Settings

- **Profile** (everyone) — change your display name (it's the same in all your organizations).
- **Organization** (Admin) — rename the organization.
- **Users & roles** (Admin) — **Invite people** by email with a role, see and revoke pending invitations; in the
  members table set each person's role, turn **Active** off to block someone's access to this organization (they keep
  their records and stay listed), or **Remove** them from the organization (their records stay, still attributed to
  them). This only affects this organization, never their account or other organizations.
- **Pipeline** (Admin) — rename each stage and set its **default probability** (the % chance a deal at that
  stage closes). Stages are Open, Won or Lost; the seven default stages are
  New → Contacted → Qualified → Proposal → Negotiation → Won / Lost.
- **Lead sources** (Admin) — connections that create leads automatically (see Leads below).
- **Audit log** (Admin, Manager) — who created, changed (field by field), converted, moved, imported or deleted
  what, who invited, changed or removed which member, and when.

The top bar also has a **theme** button: Light, Dark or System (follows your device).

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

**Importing leads from social media.** Leads can come in by themselves:

- **Settings → Lead sources** (admins): *Connect source* → **Meta Lead Ads** with your Facebook Page ID and
  Page access token. Every Facebook *and* Instagram lead-form submission on that Page becomes a lead within
  seconds; *Sync now* pulls older ones. Or choose **Webhook** to get a secret URL for X, LinkedIn, TikTok,
  YouTube, WhatsApp… — in Zapier/Make/n8n, use the platform's "new lead" trigger with a "POST webhook" action.
- **Leads → Import**: upload the CSV you downloaded from Meta Leads Center, LinkedIn Campaign Manager or
  TikTok, pick the platform, check the preview, and import.

Imported leads get status *New*, source *Social media*, a platform badge and handle, and the owner you chose
(who is notified). Extra form answers (budget, message, campaign…) are saved as a note on the lead. Leads that
already exist (same email, or the same platform lead id) are skipped. Filter the list by **Platform**.

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
read** on the Notifications page. Notifications belong to an organization: you see the ones for the organization
you're working in.

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

You can also **ask about what's already in the CRM**, for example:

> What's Vikram Khadse's phone number?
>
> Tell me about Brightwave. What did we discuss with them last time?

It looks the records up and answers from them: phone numbers and emails, company details, a company's contacts,
recent calls, meetings and notes, open tasks and deals. If nothing matches, it says so rather than guessing.
Questions don't save anything.

**Lists and files.** Ask for a list ("all contacts created by Riya", "qualified leads from the website", "companies in
Mumbai", "my tasks this week") and it tells you how many there are and names the first few. Under the answer you
get **Excel**, **Word** and **PowerPoint** buttons that download the full list straight away; or just say "yes" when
it asks *"Would you like this as an Excel file?"*. For a longer write-up (an account overview, a summary of past
calls) it offers a Word document, or PowerPoint if you mention a presentation. Ask for Markdown if you want an `.md`
file. Files are made on the spot and aren't stored anywhere.

**Talk instead of typing.** Click the **microphone** next to the message box (your browser asks for microphone
access the first time) and speak. While it's listening you'll see moving bars and a timer:

- press **Enter** (or the send button) to send what you said straight to the assistant;
- click **✓** to put the text in the box first, so you can check or fix it before sending;
- press **Esc** (or **✕**) to throw the recording away.

Your voice is turned into text on NexaCRM's own server; it isn't stored. Names already in your CRM are recognised
best, so say them the way they're saved. A recording can be up to 2 minutes. The microphone needs a secure page
(https, or localhost while developing).

Each reply lists what was saved as links; click one to open the record. Click a suggestion to start, press
**Enter** to send (**Shift+Enter** for a new line), and **New chat** to start over. The conversation is kept while
you move between pages, but not after a page reload.

Good to know:

- It can't create deals, convert leads, or delete anything. Use the normal pages for those.
- It follows your permissions: a Sales Rep can't change a teammate's lead through chat either. Everything it saves
  shows up in the audit log and sends the usual notifications.
- It only sees and changes the organization you're working in.
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
