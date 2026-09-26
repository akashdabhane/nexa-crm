import { Mail, Phone, StickyNote, Users, type LucideIcon } from "lucide-react";

export const ACTIVITY_ICONS: Record<string, { icon: LucideIcon; className: string; label: string }> = {
  call: { icon: Phone, className: "bg-sky-100 text-sky-700", label: "Call" },
  meeting: { icon: Users, className: "bg-violet-100 text-violet-700", label: "Meeting" },
  email: { icon: Mail, className: "bg-amber-100 text-amber-800", label: "Email" },
  note: { icon: StickyNote, className: "bg-slate-100 text-slate-700", label: "Note" },
};
