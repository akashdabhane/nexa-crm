"use client";

import { History, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { ActivityTimeline } from "@/components/shared/activity-timeline";
import { FilterSelect } from "@/components/shared/filter-select";
import { Pagination } from "@/components/shared/pagination";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useListState } from "@/hooks/use-list-state";
import { ACTIVITY_TYPES, type TimelineItem } from "@/types";
import { humanize } from "@/utils/format";

import { activityHooks } from "./hooks";
import { LogActivityDialog } from "./log-activity-dialog";

export function ActivitiesView() {
  const [logging, setLogging] = useState(false);
  const { canEdit } = useCurrentUser();
  const list = useListState({ filters: ["type", "owner_id", "date_from", "date_to"], defaultSort: "occurred_at" });
  const { data, isLoading, error, refetch } = activityHooks.useList(list.params);
  const remove = activityHooks.useDelete();
  const { data: users = [] } = useUsers();

  const items: TimelineItem[] = (data?.items ?? []).map((activity) => ({
    kind: "activity",
    occurred_at: activity.occurred_at,
    activity,
    note: null,
  }));

  return (
    <>
      <PageHeader
        title="Activities"
        description="Calls, meetings and emails across your team, newest first."
        actions={
          <Button onClick={() => setLogging(true)}>
            <Plus /> Log activity
          </Button>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search activities…" />
        <FilterSelect
          value={list.filters.type}
          onChange={(v) => list.setFilter("type", v)}
          placeholder="All types"
          options={ACTIVITY_TYPES.map((t) => ({ value: t, label: humanize(t) }))}
        />
        <FilterSelect
          value={list.filters.owner_id}
          onChange={(v) => list.setFilter("owner_id", v)}
          placeholder="Everyone"
          options={users.map((u) => ({ value: u.id, label: u.full_name }))}
        />
        <div className="flex items-center gap-2">
          <Input type="date" aria-label="From date" className="w-full sm:w-38" value={list.filters.date_from} onChange={(e) => list.setFilter("date_from", e.target.value)} />
          <span className="text-muted-foreground">–</span>
          <Input type="date" aria-label="To date" className="w-full sm:w-38" value={list.filters.date_to} onChange={(e) => list.setFilter("date_to", e.target.value)} />
        </div>
        {list.hasActiveFilters && (
          <Button variant="ghost" onClick={list.clearFilters}>
            Clear filters
          </Button>
        )}
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <Card>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64" />
            ) : items.length ? (
              <ActivityTimeline
                items={items}
                canDelete={(item) => item.kind === "activity" && canEdit(item.activity)}
                onDelete={(item) => item.activity && remove.mutate(item.activity.id)}
              />
            ) : (
              <EmptyState icon={History} title="No activities found" description="Log calls, meetings and emails to build a history." />
            )}
          </CardContent>
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />}

      <LogActivityDialog open={logging} onOpenChange={setLogging} />
    </>
  );
}
