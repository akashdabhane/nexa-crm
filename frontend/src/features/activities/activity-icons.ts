import { Mail, Phone, StickyNote, Users, type LucideIcon } from "lucide-react";

export const ACTIVITY_ICONS: Record<string, { icon: LucideIcon; className: string; label: string }> = {
  call: { icon: Phone, className: "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300", label: "Call" },
  meeting: { icon: Users, className: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300", label: "Meeting" },
  email: { icon: Mail, className: "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300", label: "Email" },
  note: { icon: StickyNote, className: "bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300", label: "Note" },
};
