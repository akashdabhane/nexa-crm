"use client";

import { CheckSquare, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { FilterSelect } from "@/components/shared/filter-select";
import { Pagination } from "@/components/shared/pagination";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { taskHooks } from "@/features/activities/hooks";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useListState } from "@/hooks/use-list-state";
import { TASK_PRIORITIES, TASK_STATUSES, type ListParams, type Task } from "@/types";
import { humanize } from "@/utils/format";

import { TaskFormDialog } from "./task-form-dialog";
import { TaskItem } from "./task-item";

const VIEWS = {
  open: { label: "Open", params: { open_only: true } },
  overdue: { label: "Overdue", params: { overdue: true } },
  completed: { label: "Completed", params: { status: "completed" } },
  all: { label: "All", params: {} },
} satisfies Record<string, { label: string; params: ListParams }>;
type View = keyof typeof VIEWS;

export function TasksView() {
  const { user } = useCurrentUser();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Task | undefined>();
  const list = useListState({ filters: ["view", "priority", "status", "owner_id", "mine"], defaultSort: "due_date", defaultOrder: "asc" });
  const view: View = (list.filters.view as View) in VIEWS ? (list.filters.view as View) : "open";
  const mine = list.filters.mine !== "false";

  const params: ListParams = {
    ...list.params,
    view: undefined,
    mine: undefined,
    ...VIEWS[view].params,
    ...(list.filters.status ? { status: list.filters.status } : {}),
    owner_id: mine ? user?.id : list.filters.owner_id || undefined,
  };
  const { data, isLoading, error, refetch } = taskHooks.useList(params, { enabled: Boolean(user) });
  const { data: users = [] } = useUsers();

  return (
    <>
      <PageHeader
        title="Tasks"
        description="Follow-ups and to-dos for you and your team."
        actions={
          <Button
            onClick={() => {
              setEditing(undefined);
              setFormOpen(true);
            }}
          >
            <Plus /> New task
          </Button>
        }
      />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Tabs value={view} onValueChange={(v) => list.setFilter("view", v === "open" ? "" : v)}>
          <TabsList>
            {Object.entries(VIEWS).map(([key, { label }]) => (
              <TabsTrigger key={key} value={key}>
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Tabs value={mine ? "mine" : "team"} onValueChange={(v) => list.setFilter("mine", v === "mine" ? "" : "false")}>
          <TabsList>
            <TabsTrigger value="mine">My tasks</TabsTrigger>
            <TabsTrigger value="team">Team</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search tasks…" />
        <FilterSelect
          value={list.filters.priority}
          onChange={(v) => list.setFilter("priority", v)}
          placeholder="All priorities"
          options={TASK_PRIORITIES.map((p) => ({ value: p, label: humanize(p) }))}
        />
        {view === "all" && (
          <FilterSelect
            value={list.filters.status}
            onChange={(v) => list.setFilter("status", v)}
            placeholder="All statuses"
            options={TASK_STATUSES.map((s) => ({ value: s, label: humanize(s) }))}
          />
        )}
        {!mine && (
          <FilterSelect
            value={list.filters.owner_id}
            onChange={(v) => list.setFilter("owner_id", v)}
            placeholder="All assignees"
            options={users.map((u) => ({ value: u.id, label: u.full_name }))}
          />
        )}
        <FilterSelect
          value={list.sortBy}
          onChange={(v) => (v === "priority" || v === "created_at" ? list.setSortTo(v, "desc") : list.setSortTo(v || "due_date", "asc"))}
          placeholder="Sort by due date"
          options={[
            { value: "priority", label: "Sort by priority" },
            { value: "created_at", label: "Sort by created" },
            { value: "title", label: "Sort by title" },
          ]}
        />
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : isLoading || !data ? (
        <Skeleton className="h-64" />
      ) : data.items.length === 0 ? (
        <Card>
          <EmptyState icon={CheckSquare} title={view === "overdue" ? "Nothing overdue 🎉" : "No tasks here"} description="Tasks you create or are assigned appear here." />
        </Card>
      ) : (
        <Card className="gap-0 divide-y py-0">
          {data.items.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              onEdit={(t) => {
                setEditing(t);
                setFormOpen(true);
              }}
            />
          ))}
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />}

      <TaskFormDialog open={formOpen} onOpenChange={setFormOpen} task={editing} />
    </>
  );
}
