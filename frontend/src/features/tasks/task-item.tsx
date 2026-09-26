"use client";

import { CalendarDays, Pencil } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { taskHooks } from "@/features/activities/hooks";
import { useCurrentUser } from "@/hooks/use-current-user";
import { cn } from "@/lib/utils";
import type { Task } from "@/types";
import { formatDate } from "@/utils/format";

/** One task row with a completion checkbox. */
export function TaskItem({ task, onEdit, showLinks = true }: { task: Task; onEdit?: (task: Task) => void; showLinks?: boolean }) {
  const { canEdit } = useCurrentUser();
  const update = taskHooks.useUpdate();
  const done = task.status === "completed";
  const editable = canEdit(task);
  const related = [task.deal && { href: `/deals/${task.deal.id}`, ...task.deal }, task.contact && { href: `/contacts/${task.contact.id}`, ...task.contact }, task.company && { href: `/companies/${task.company.id}`, ...task.company }].filter(
    Boolean,
  ) as { href: string; id: string; name: string }[];

  return (
    <div className="group flex items-start gap-3 p-3">
      <Checkbox
        className="mt-0.5"
        checked={done}
        disabled={!editable || update.isPending}
        onCheckedChange={(checked) => update.mutate({ id: task.id, data: { status: checked ? "completed" : "pending" } })}
        aria-label={done ? "Mark as not done" : "Mark as done"}
      />
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm font-medium", done && "text-muted-foreground line-through")}>{task.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {task.due_date && (
            <span className={cn("inline-flex items-center gap-1", task.is_overdue && "font-medium text-rose-600")}>
              <CalendarDays className="size-3" /> {task.is_overdue ? "Overdue · " : ""}
              {formatDate(task.due_date)}
            </span>
          )}
          {showLinks &&
            related.map((link) => (
              <Link key={link.href} href={link.href} className="hover:text-foreground hover:underline">
                {link.name}
              </Link>
            ))}
          {task.owner && <span>{task.owner.full_name}</span>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {task.status === "in_progress" || task.status === "cancelled" ? <StatusBadge value={task.status} /> : null}
        <StatusBadge value={task.priority} />
        {onEdit && editable && (
          <Button variant="ghost" size="icon-xs" className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" onClick={() => onEdit(task)} aria-label="Edit task">
            <Pencil />
          </Button>
        )}
      </div>
    </div>
  );
}
