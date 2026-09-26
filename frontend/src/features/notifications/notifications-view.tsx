"use client";

import { Bell, CheckCheck } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useListState } from "@/hooks/use-list-state";

import { useMarkAllRead, useMarkRead, useNotifications, useUnreadCount } from "./hooks";
import { NotificationItem } from "./notification-item";

export function NotificationsView() {
  const list = useListState({ filters: ["unread"] });
  const unreadOnly = list.filters.unread === "true";
  const { data, isLoading, error, refetch } = useNotifications({ page: list.page, page_size: 20, unread_only: unreadOnly });
  const { data: unread = 0 } = useUnreadCount();
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Assignments, due tasks and closed deals."
        actions={
          <Button variant="outline" disabled={unread === 0 || markAll.isPending} onClick={() => markAll.mutate()}>
            <CheckCheck /> Mark all as read
          </Button>
        }
      />
      <Tabs value={unreadOnly ? "unread" : "all"} onValueChange={(v) => list.setFilter("unread", v === "unread" ? "true" : "")}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">Unread ({unread})</TabsTrigger>
        </TabsList>
      </Tabs>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : isLoading || !data ? (
        <Skeleton className="h-64" />
      ) : data.items.length === 0 ? (
        <Card>
          <EmptyState icon={Bell} title={unreadOnly ? "No unread notifications" : "No notifications yet"} />
        </Card>
      ) : (
        <Card className="gap-1 p-2">
          {data.items.map((n) => (
            <NotificationItem key={n.id} notification={n} onOpen={(item) => !item.is_read && markRead.mutate(item.id)} />
          ))}
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />}
    </>
  );
}
