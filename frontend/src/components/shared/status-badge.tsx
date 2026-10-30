import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { humanize } from "@/utils/format";

type Tone = "gray" | "blue" | "green" | "amber" | "red" | "violet" | "indigo" | "sky";

const TONES: Record<Tone, string> = {
  gray: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30",
  blue: "bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30",
  sky: "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-500/30",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/30",
  violet: "bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/15 dark:text-violet-300 dark:ring-violet-500/30",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30",
  amber: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30",
  red: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/30",
};

/** One place that decides the color of every status / priority / type value. */
const VALUE_TONES: Record<string, Tone> = {
  // contacts
  active: "blue",
  customer: "green",
  inactive: "gray",
  // leads
  new: "sky",
  contacted: "indigo",
  qualified: "violet",
  unqualified: "gray",
  converted: "green",
  // deals
  open: "blue",
  won: "green",
  lost: "red",
  // tasks
  pending: "gray",
  in_progress: "blue",
  completed: "green",
  cancelled: "gray",
  low: "gray",
  medium: "sky",
  high: "amber",
  urgent: "red",
  // activities
  call: "sky",
  meeting: "violet",
  email: "amber",
  note: "gray",
  // roles
  admin: "violet",
  manager: "indigo",
  sales_rep: "gray",
};

export function StatusBadge({ value, label, className }: { value: string; label?: string; className?: string }) {
  const tone = VALUE_TONES[value] ?? "gray";
  return (
    <Badge variant="outline" className={cn("border-0 font-medium ring-1 ring-inset", TONES[tone], className)}>
      {label ?? humanize(value)}
    </Badge>
  );
}
