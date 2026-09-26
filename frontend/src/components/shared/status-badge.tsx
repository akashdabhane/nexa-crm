import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { humanize } from "@/utils/format";

type Tone = "gray" | "blue" | "green" | "amber" | "red" | "violet" | "indigo" | "sky";

const TONES: Record<Tone, string> = {
  gray: "bg-slate-100 text-slate-700 ring-slate-200",
  blue: "bg-blue-50 text-blue-700 ring-blue-200",
  sky: "bg-sky-50 text-sky-700 ring-sky-200",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber: "bg-amber-50 text-amber-800 ring-amber-200",
  red: "bg-rose-50 text-rose-700 ring-rose-200",
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
