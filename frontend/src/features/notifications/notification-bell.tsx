"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";

import { useMarkAllRead, useMarkRead, useNotifications, useUnreadCount } from "./hooks";
import { NotificationItem } from "./notification-item";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { data: count = 0 } = useUnreadCount();
  const { data, isLoading } = useNotifications({ page_size: 6 });
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label={`Notifications (${count} unread)`}>
          <Bell />
          {count > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(24rem,calc(100vw-2rem))] p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <p className="font-semibold">Notifications</p>
          {count > 0 && (
            <Button variant="link" size="sm" className="h-auto p-0" onClick={() => markAll.mutate()}>
              Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-96 overflow-y-auto p-1">
          {isLoading ? (
            <Skeleton className="m-2 h-24" />
          ) : data?.items.length ? (
            data.items.map((n) => (
              <NotificationItem
                key={n.id}
                notification={n}
                compact
                onOpen={(item) => {
                  if (!item.is_read) markRead.mutate(item.id);
                  setOpen(false);
                }}
              />
            ))
          ) : (
            <p className="p-6 text-center text-sm text-muted-foreground">You&apos;re all caught up.</p>
          )}
        </div>
        <div className="border-t p-2">
          <Button variant="ghost" size="sm" className="w-full" asChild onClick={() => setOpen(false)}>
            <Link href="/notifications">View all notifications</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
