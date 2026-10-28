# Design System

NexaCRM should look like a modern SaaS CRM: calm neutral surfaces, one indigo brand color, dense-but-readable
tables, and clear status colors. Everything is built from **shadcn/ui (style `radix-nova`) + Tailwind CSS v4**.

## Principles

1. **Consistency over novelty** — every list page, record page and form follows the same layout (below). Build new screens by composing the shared components, not by inventing new patterns.
2. **Data first** — tables and numbers are the product. Use `tabular-nums` for figures, right-align money columns, keep chrome recessive.
3. **Every state is designed** — loading (`Skeleton`, `DataTable` skeleton rows), empty (`EmptyState` with a helpful hint), error (`ErrorState` with *Try again*), success/failure feedback (`sonner` toasts).
4. **Permission-aware UI** — hide actions the user can't perform (`useCurrentUser().canEdit(record)`, `isManager`, `isAdmin`), but never rely on hiding for security.
5. **Fast data entry** — create/edit in dialogs, not separate pages; sensible defaults (owner = me, stage = first, now for activity time).

## Theme tokens (`frontend/src/app/globals.css`)

Tokens are CSS custom properties consumed through Tailwind (`bg-primary`, `text-muted-foreground`, `border`, …).
Never hard-code brand colors in components — use the tokens.

| Token | Light | Dark (`.dark`) | Use |
|---|---|---|---|
| `--primary` | `oklch(0.511 0.262 276.966)` (indigo-600) | `oklch(0.673 0.182 276.935)` (indigo-400) | Brand, primary buttons, active nav, links |
| `--primary-foreground` | `oklch(0.985 0 0)` | `oklch(0.985 0 0)` | Text on primary |
| `--ring` | `oklch(0.585 0.233 277.117)` | indigo-400 | Focus rings |
| `--background` / `--foreground` | white / near-black | near-black / white | Page |
| `--muted`, `--muted-foreground`, `--border`, `--card`, `--popover`, `--destructive` | shadcn neutral defaults | shadcn neutral defaults | Surfaces and text hierarchy |
| `--sidebar-*` | neutral, `--sidebar-primary` = brand | — | App sidebar |
| `--radius` | `0.625rem` (derived `--radius-sm…4xl`) | — | Corner rounding |

**Chart palette** (validated for color-vision deficiency and contrast; do not change without re-validating):

| Slot | Light | Dark |
|---|---|---|
| `--chart-1` (blue) | `#2a78d6` | `#3987e5` |
| `--chart-2` (orange) | `#eb6834` | `#d95926` |
| `--chart-3` (aqua) | `#1baf7a` | `#199e70` |
| `--chart-4` (yellow) | `#eda100` | `#c98500` |
| `--chart-5` (magenta) | `#e87ba4` | `#d55181` |

Single-series charts use `--chart-1`; two series use `--chart-1` then `--chart-2`, in that fixed order.
`--chart-3` is below 3:1 contrast on white — only use it with visible labels or a table.

**Dark mode:** `.dark` tokens exist, but there is no theme toggle and no `ThemeProvider`. The app ships light-only
today. If you add dark mode, add a toggle via `next-themes` and check every hard-coded Tailwind palette class
(badge tones, activity icons, alerts).

## Typography

- **Geist Sans** (`next/font/google`, CSS variable `--font-sans`) for all UI; **Geist Mono** (`--font-geist-mono`) for code-like values (e.g. audit action names use `font-mono text-xs`).
- Page title: `text-2xl font-semibold tracking-tight` (`PageHeader`, `RecordHeader`). Card title: shadcn `CardTitle`. Body `text-sm`; meta/hints `text-xs text-muted-foreground`.
- KPI numbers: `text-2xl font-semibold tabular-nums` (`StatCard`).

## Status colors

One map decides every status/priority/type color: `VALUE_TONES` (value → tone) and `TONES` (tone → classes) in
`frontend/src/components/shared/status-badge.tsx` (`<StatusBadge value="won" />`). Add new enum values there — never color a badge ad hoc.

| Tone | Values |
|---|---|
| green | `customer`, `converted`, `won`, `completed` |
| red | `lost`, `urgent` |
| amber | `high`, `email` |
| blue / sky / indigo / violet | `active`, `open`, `in_progress`, `new`, `medium`, `call`, `contacted`, `meeting`, `qualified`, `admin`, `manager` |
| gray | `inactive`, `unqualified`, `pending`, `cancelled`, `low`, `note`, `sales_rep` |

Badges always show a **text label**, so color is never the only signal. Activity type icons and colors live in
`frontend/src/features/activities/activity-icons.ts`; notification icons in `features/notifications/notification-item.tsx`.

## Layout & breakpoints

Tailwind v4 default breakpoints: `sm` 640px · `md` 768px · `lg` 1024px · `xl` 1280px. `useIsMobile()`
(`src/hooks/use-mobile.ts`) treats < 768px as mobile (the sidebar becomes a sheet).

- **App shell** (`src/app/(app)/layout.tsx`): collapsible icon sidebar (`components/layout/app-sidebar.tsx`, nav in `nav-items.ts`), sticky top bar with sidebar trigger, the **AI Assistant** button (outline, `Sparkles` icon in `text-primary`, label hidden below `sm`) and the notification bell, `main` with `p-4 md:p-6 space-y-6`.
- **Auth pages** (`src/app/(auth)/layout.tsx`): split screen — form on the left, indigo brand panel on the right from `lg`.
- Grids collapse to one column on mobile: KPI tiles `sm:grid-cols-2 xl:grid-cols-4`; record pages `lg:grid-cols-3` (details card + 2-column tabs); filter rows `flex-col sm:flex-row sm:flex-wrap`.
- Wide tables scroll horizontally inside their card (`overflow-x-auto`); the Kanban board scrolls horizontally with fixed `w-72` columns.

## Page patterns (compose these)

| Pattern | Components |
|---|---|
| **List page** | `PageHeader` (title, description, primary "New …" button) → filter row (`SearchInput`, `FilterSelect`s, "Clear filters") → `DataTable` (sortable headers, row click → detail) → `Pagination`. State via `useListState` (URL). See `features/contacts/contacts-view.tsx`. |
| **Record page** | `RecordHeader` (back link, avatar, title, badges, Edit, ⋯ Delete) → optional stats/`StageProgress` → grid: Details `Card` with `DetailList` + `RecordTabs` (Timeline, related lists, Tasks, Notes). See `features/deals/deal-detail.tsx`. |
| **Create/Edit form** | shadcn `Dialog` with a `<form id>` body (`grid sm:grid-cols-2 gap-4`, scrollable `max-h-[65vh]`), `FormField` wrappers, footer Cancel + submit (`form="…"`). Selects via `Controller`. Related records via `EntityCombobox`; users via `UserSelect`. |
| **Destructive action** | `ConfirmDialog` (stays open while pending) — never delete on a single click. |
| **Dashboard/report** | `StatCard` tiles → `Card`s with `BarChart` or tables. |
| **Side panel / chat** | shadcn `Sheet` from the right (full width on mobile, `sm:max-w-md`): header with title + description, scrollable body, form pinned to the bottom. User bubbles `bg-primary text-primary-foreground` on the right, assistant bubbles `bg-muted` on the left; saved records as small bordered link rows with a type icon and "lead created"-style label; "Working on it…" spinner while pending; errors as toasts with the draft restored. See `features/assistant/assistant-sheet.tsx`. |

## Shared component inventory

`frontend/src/components/shared/`: `data-table`, `pagination`, `search-input` (300ms debounce), `filter-select`,
`states` (`EmptyState`, `ErrorState`, `DetailSkeleton`), `confirm-dialog`, `status-badge`, `entity-combobox`,
`user-select` (+ `useUsers`), `user-avatar` (initials, stable color), `owner-cell`, `detail-list`, `record-header`,
`record-tabs`, `form-field`, `kanban-board`, `activity-timeline`, `bar-chart`, `stat-card`.
`frontend/src/components/layout/`: `app-sidebar`, `topbar` (hosts `AssistantSheet` and `NotificationBell`), `user-menu`, `page-header`, `logo`, `nav-items`.
`frontend/src/components/ui/`: shadcn primitives — generated; don't hand-edit unless necessary.

## Charts

Use `components/shared/bar-chart.tsx` (Recharts through shadcn `ChartContainer`). Rules:
thin bars with 4px rounded ends anchored to the baseline; recessive dashed grid; **one y-axis only (never dual
axis)**; hover tooltip that shows the value first; legend only when there are ≥ 2 series; a table or direct labels
next to any chart whose numbers matter (reports do this). For progress-style comparisons, a simple
`h-1.5 rounded-full` bar is fine (lead sources).

## Accessibility (target: WCAG 2.1 AA)

- Every input has a visible `<Label htmlFor>` via `FormField`; errors are rendered as text under the field.
- Icon-only buttons need `aria-label` (see pagination, row actions, the notification bell with its unread count, the assistant's Send button and message box).
- Custom controls declare roles (the activity type picker is a `radiogroup` with `aria-checked`); alerts use `role="alert"` / `role="status"`.
- Keep Radix/shadcn focus styles; don't remove outlines. Hover-revealed actions must also appear on `focus-visible`/`focus-within`.
- Never encode meaning by color alone (badges have text, overdue dates say "Overdue", charts have labels/tables).
- Text contrast ≥ 4.5:1 using the token palette; don't put `--muted-foreground` text on colored backgrounds.
- Drag-and-drop always has a keyboard/touch alternative (the Kanban card "Move to" menu, the deal page stage path).
