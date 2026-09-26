import Link from "next/link";

import { cn } from "@/lib/utils";

export function Logo({ className, collapsed = false }: { className?: string; collapsed?: boolean }) {
  return (
    <Link href="/dashboard" className={cn("flex items-center gap-2 font-semibold", className)}>
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
        N
      </span>
      {!collapsed && <span className="text-lg tracking-tight">NexaCRM</span>}
    </Link>
  );
}
