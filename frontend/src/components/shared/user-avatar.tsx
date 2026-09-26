import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

const COLORS = [
  "bg-indigo-100 text-indigo-700",
  "bg-sky-100 text-sky-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-700",
  "bg-violet-100 text-violet-700",
];

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

/** Initials avatar with a stable color derived from the name. */
export function UserAvatar({ name, className }: { name: string; className?: string }) {
  const color = COLORS[[...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % COLORS.length];
  return (
    <Avatar className={cn("size-7", className)}>
      <AvatarFallback className={cn("text-xs font-medium", color)}>{initials(name) || "?"}</AvatarFallback>
    </Avatar>
  );
}
