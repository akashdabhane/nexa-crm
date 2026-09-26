"use client";

import { CheckSquare, Plus } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { taskHooks } from "@/features/activities/hooks";
import type { Task } from "@/types";

import { TaskFormDialog, type TaskDefaults } from "./task-form-dialog";
import { TaskItem } from "./task-item";

/** Tasks tab on a record page. `filter` selects tasks, `defaults` pre-fills new ones. */
export function RecordTasks({ filter, defaults }: { filter: Record<string, string>; defaults: TaskDefaults }) {
  const [editing, setEditing] = useState<Task | undefined>();
  const [formOpen, setFormOpen] = useState(false);
  const { data, isLoading } = taskHooks.useList({ ...filter, page_size: 50, sort_by: "due_date", sort_order: "asc" });

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setEditing(undefined);
            setFormOpen(true);
          }}
        >
          <Plus /> Add task
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data?.items.length ? (
        <div className="divide-y rounded-lg border">
          {data.items.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              showLinks={false}
              onEdit={(t) => {
                setEditing(t);
                setFormOpen(true);
              }}
            />
          ))}
        </div>
      ) : (
        <EmptyState icon={CheckSquare} title="No tasks" description="Plan the next follow-up." />
      )}
      <TaskFormDialog open={formOpen} onOpenChange={setFormOpen} task={editing} defaults={defaults} />
    </div>
  );
}
