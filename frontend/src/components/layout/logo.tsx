import Link from "next/link";

import { cn } from "@/lib/utils";

/** The NexaCRM mark: same artwork as the favicon (see scripts/generate-icons.mjs). */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg bg-linear-135 from-[#7c6cff] via-[#4f39f6] to-[#3a24c9]",
        className,
      )}
    >
      <svg viewBox="0 0 64 64" className="size-full" aria-hidden="true">
        <path d="M20 45V19l24 26V31" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="44" cy="19" r="5" fill="#67e8f9" />
      </svg>
    </span>
  );
}

export function Logo({
  className,
  collapsed = false,
  href = "/dashboard",
}: {
  className?: string;
  collapsed?: boolean;
  href?: string;
}) {
  return (
    <Link href={href} className={cn("flex items-center gap-2 font-semibold", className)} aria-label="NexaCRM home">
      <LogoMark />
      {!collapsed && <span className="text-lg tracking-tight">NexaCRM</span>}
    </Link>
  );
}
