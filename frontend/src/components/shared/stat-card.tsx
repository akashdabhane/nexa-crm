import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type StatCardProps = {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  href?: string;
  className?: string;
};

/** A single headline number (KPI tile). */
export function StatCard({ label, value, hint, icon: Icon, href, className }: StatCardProps) {
  const body = (
    <Card className={cn("gap-0 py-4 transition-colors", href && "hover:border-primary/40 hover:bg-muted/30", className)}>
      <CardContent className="px-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">{label}</p>
          {Icon && <Icon className="size-4 text-muted-foreground" />}
        </div>
        <p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export function StatCardSkeleton() {
  return <Skeleton className="h-[98px] rounded-xl" />;
}
