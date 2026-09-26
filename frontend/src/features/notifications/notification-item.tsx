"use client";

import { AlarmClock, Handshake, ListTodo, Target, Trophy, XCircle, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";
import { entityHref } from "@/services/notifications";
import type { AppNotification, NotificationType } from "@/types";
import { formatRelative } from "@/utils/format";

const ICONS: Record<NotificationType, { icon: LucideIcon; className: string }> = {
  lead_assigned: { icon: Target, className: "bg-sky-100 text-sky-700" },
  deal_assigned: { icon: Handshake, className: "bg-indigo-100 text-indigo-700" },
  task_assigned: { icon: ListTodo, className: "bg-violet-100 text-violet-700" },
  task_due: { icon: AlarmClock, className: "bg-amber-100 text-amber-800" },
  deal_won: { icon: Trophy, className: "bg-emerald-100 text-emerald-700" },
  deal_lost: { icon: XCircle, className: "bg-rose-100 text-rose-700" },
};

export function NotificationItem({
  notification,
  onOpen,
  compact = false,
}: {
  notification: AppNotification;
  onOpen?: (notification: AppNotification) => void;
  compact?: boolean;
}) {
  const { icon: Icon, className } = ICONS[notification.type] ?? ICONS.task_due;
  const href = entityHref(notification.entity_type, notification.entity_id);
  const body = (
    <div className={cn("flex gap-3 rounded-lg p-3 transition-colors hover:bg-muted/60", !notification.is_read && "bg-primary/5")}>
      <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full", className)}>
        <Icon className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm", !notification.is_read && "font-medium")}>{notification.title}</p>
        {notification.message && !compact && <p className="text-sm text-muted-foreground">{notification.message}</p>}
        <p className="mt-0.5 text-xs text-muted-foreground">{formatRelative(notification.created_at)}</p>
      </div>
      {!notification.is_read && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
    </div>
  );
  return href ? (
    <Link href={href} onClick={() => onOpen?.(notification)} className="block">
      {body}
    </Link>
  ) : (
    <button type="button" className="block w-full text-left" onClick={() => onOpen?.(notification)}>
      {body}
    </button>
  );
}
