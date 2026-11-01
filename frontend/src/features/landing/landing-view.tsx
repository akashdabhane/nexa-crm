import {
  ArrowRight,
  BarChart3,
  CheckSquare,
  KanbanSquare,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Logo, LogoMark } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Users,
    title: "Contact & company management",
    body: "One source of truth for every person and account, with tags, owners, search, filters and a full activity timeline.",
  },
  {
    icon: Target,
    title: "Lead management & scoring",
    body: "Track lead source, status and a 0–100 score, then convert a qualified lead into a contact, company and deal in one click.",
  },
  {
    icon: KanbanSquare,
    title: "Drag-and-drop sales pipeline",
    body: "A visual Kanban board for your deals. Moving a card updates the stage, probability and close date and notifies the team.",
  },
  {
    icon: Sparkles,
    title: "AI sales assistant",
    body: "Describe your day in plain language. The assistant creates the leads, calls, notes and follow-up tasks for you.",
  },
  {
    icon: CheckSquare,
    title: "Tasks, activities & reminders",
    body: "Log calls, meetings and emails, schedule follow-ups with due dates and priorities, and never miss an overdue task.",
  },
  {
    icon: BarChart3,
    title: "Sales reports & dashboards",
    body: "Pipeline value, revenue by month, win rate, lead conversion, lead sources and rep performance, filtered by date.",
  },
];

const STEPS = [
  { title: "Capture leads", body: "Add prospects by hand or just tell the AI assistant about them." },
  { title: "Qualify & convert", body: "Score leads and convert the good ones into a contact, company and deal." },
  { title: "Work the pipeline", body: "Drag deals through your stages and keep every call and task attached." },
  { title: "Close & report", body: "Mark deals won or lost and see what's working on the dashboard." },
];

const PIPELINE = [
  { stage: "Qualified", deals: [["Brightwave", "$12,400"], ["Northpeak", "$8,000"]] },
  { stage: "Proposal", deals: [["Lumen Labs", "$21,500"]] },
  { stage: "Negotiation", deals: [["Orbitly", "$34,000"], ["Kestrel", "$9,750"]] },
  { stage: "Won", deals: [["Acme Corp", "$18,200"]] },
];

const FAQ = [
  {
    q: "What is NexaCRM?",
    a: "NexaCRM is a customer relationship management (CRM) app for small sales teams. It keeps contacts, companies, leads and deals in one place, with a drag-and-drop sales pipeline, tasks, activity tracking, reports and a built-in AI assistant.",
  },
  {
    q: "Who is NexaCRM for?",
    a: "Sales reps who want to log their work quickly, sales managers who need visibility into the team's pipeline and performance, and owners who want simple, predictable permissions.",
  },
  {
    q: "How does the AI sales assistant work?",
    a: "Open the assistant and describe what happened, for example “Cold-called Priya at Brightwave, she wants a demo next week”. It looks for existing records first, then creates or updates the lead, logs the call and schedules the follow-up, using the same permissions and audit trail as the regular forms.",
  },
  {
    q: "Can I control who edits records?",
    a: "Yes. NexaCRM has Admin, Manager and Sales Rep roles. Everyone can see the book of business, reps can change only what they own, and an audit log records who changed what and when.",
  },
  {
    q: "What sales reports are included?",
    a: "Lead conversion, sales pipeline by stage, revenue by month, won vs lost deals, sales rep performance and lead source performance, all with date filters.",
  },
];

export function LandingView() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-6" aria-label="Main">
          <Logo href="/" />
          <div className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#how-it-works" className="hover:text-foreground">How it works</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" asChild>
              <Link href="/login">Log in</Link>
            </Button>
            <Button asChild className="hidden sm:inline-flex">
              <Link href="/signup">Get started</Link>
            </Button>
          </div>
        </nav>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 -top-40 -z-10 mx-auto h-[480px] max-w-4xl rounded-full bg-primary/15 blur-3xl"
          />
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 md:px-6 md:py-24 lg:grid-cols-2">
            <div className="space-y-6">
              <p className="inline-flex items-center gap-1.5 rounded-full border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="size-3.5 text-primary" />
                CRM with a built-in AI sales assistant
              </p>
              <h1 className="text-4xl font-bold tracking-tight text-balance sm:text-5xl">
                The AI-powered CRM for <span className="text-primary">small sales teams</span>
              </h1>
              <p className="max-w-xl text-lg text-pretty text-muted-foreground">
                Manage contacts, leads and deals on a drag-and-drop pipeline, keep every call and task in one place, and
                let an AI assistant turn your notes into CRM records.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" asChild className="h-10 px-4">
                  <Link href="/signup">
                    Get started <ArrowRight data-icon="inline-end" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild className="h-10 px-4">
                  <Link href="/login">Log in</Link>
                </Button>
              </div>
            </div>

            <PipelinePreview />
          </div>
        </section>

        {/* Features */}
        <section id="features" className="scroll-mt-16 border-t bg-muted/40">
          <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 md:px-6 md:py-24">
            <div className="mx-auto max-w-2xl space-y-3 text-center">
              <h2 className="text-3xl font-bold tracking-tight">Everything your sales team needs in one CRM</h2>
              <p className="text-muted-foreground">
                From the first touch to the closed deal: lead tracking, pipeline management, activity logging and
                sales reporting, without the enterprise complexity.
              </p>
            </div>
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, body }) => (
                <li key={title} className="space-y-3 rounded-xl border bg-card p-6 text-card-foreground">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="text-sm text-muted-foreground">{body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="scroll-mt-16 border-t">
          <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 md:px-6 md:py-24">
            <div className="mx-auto max-w-2xl space-y-3 text-center">
              <h2 className="text-3xl font-bold tracking-tight">From lead to closed deal</h2>
              <p className="text-muted-foreground">A simple sales process your whole team can follow.</p>
            </div>
            <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map(({ title, body }, index) => (
                <li key={title} className="space-y-2">
                  <span className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                    {index + 1}
                  </span>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="text-sm text-muted-foreground">{body}</p>
                </li>
              ))}
            </ol>

            <div className="grid gap-6 rounded-2xl border bg-card p-6 md:grid-cols-2 md:p-10">
              <div className="space-y-3">
                <h3 className="flex items-center gap-2 text-xl font-semibold">
                  <Sparkles className="size-5 text-primary" /> Data entry, done for you
                </h3>
                <p className="text-muted-foreground">
                  Reps skip logging because forms are tedious. With NexaCRM they type one sentence and the assistant
                  records it with the same validation, permissions and audit trail as the forms.
                </p>
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <ShieldCheck className="size-4 text-primary" /> Role-based permissions and a full audit log.
                </p>
              </div>
              <div className="space-y-3 text-sm" aria-hidden="true">
                <p className="ml-auto max-w-xs rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-primary-foreground">
                  Cold-called Priya at Brightwave, she wants a demo next week.
                </p>
                <div className="max-w-xs space-y-1.5 rounded-2xl rounded-bl-sm border bg-muted/50 px-4 py-2.5">
                  <p>Done! I saved:</p>
                  <ul className="list-inside list-disc text-muted-foreground">
                    <li>Lead: Priya · Brightwave</li>
                    <li>Call logged today</li>
                    <li>Task: Schedule demo, due next week</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="scroll-mt-16 border-t bg-muted/40">
          <div className="mx-auto max-w-3xl space-y-8 px-4 py-16 md:px-6 md:py-24">
            <h2 className="text-center text-3xl font-bold tracking-tight">Frequently asked questions</h2>
            <div className="divide-y rounded-xl border bg-card">
              {FAQ.map(({ q, a }) => (
                <details key={q} className="group p-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                    <h3>{q}</h3>
                    <span className="text-muted-foreground transition-transform group-open:rotate-45" aria-hidden="true">
                      +
                    </span>
                  </summary>
                  <p className="mt-3 text-sm text-muted-foreground">{a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* Call to action */}
        <section className="border-t">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-5 px-4 py-16 text-center md:px-6 md:py-24">
            <LogoMark className="size-12 rounded-xl" />
            <h2 className="text-3xl font-bold tracking-tight">Start managing your pipeline today</h2>
            <p className="max-w-xl text-muted-foreground">
              Create your account and bring your contacts, leads and deals into one place.
            </p>
            <Button size="lg" asChild className="h-10 px-4">
              <Link href="/signup">
                Create your account <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground sm:flex-row md:px-6">
          <p>
            © {new Date().getFullYear()} {site.name}. {site.tagline}.
          </p>
          <nav className="flex gap-4" aria-label="Footer">
            <Link href="/login" className="hover:text-foreground">Log in</Link>
            <Link href="/signup" className="hover:text-foreground">Sign up</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

/** Decorative mini Kanban board for the hero. */
function PipelinePreview() {
  return (
    <div aria-hidden="true" className="rounded-2xl border bg-card p-4 shadow-xl shadow-primary/10 md:p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-semibold">Sales pipeline</p>
        <p className="text-xs text-muted-foreground">Weighted value $64,320</p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {PIPELINE.map(({ stage, deals }) => (
          <div key={stage} className="space-y-2 rounded-lg bg-muted/60 p-2">
            <p className="px-1 text-xs font-medium text-muted-foreground">{stage}</p>
            {deals.map(([name, value]) => (
              <div key={name} className="rounded-md border bg-background p-2 shadow-xs">
                <p className="truncate text-xs font-medium">{name}</p>
                <p className={stage === "Won" ? "text-xs text-emerald-600 dark:text-emerald-400" : "text-xs text-muted-foreground"}>
                  {value}
                </p>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
