"use client";

import { CalendarDays, MoreVertical, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { FilterSelect } from "@/components/shared/filter-select";
import { KanbanBoard } from "@/components/shared/kanban-board";
import { SearchInput } from "@/components/shared/search-input";
import { ErrorState } from "@/components/shared/states";
import { UserAvatar } from "@/components/shared/user-avatar";
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useListState } from "@/hooks/use-list-state";
import type { Deal, Stage } from "@/types";
import { formatCurrency, formatDate } from "@/utils/format";

import { DealFormDialog } from "./deal-form-dialog";
import { useDealBoard, useMoveDeal } from "./hooks";

const ACCENTS: Record<Stage["stage_type"], string> = {
  open: "border-t-primary",
  won: "border-t-emerald-500",
  lost: "border-t-rose-500",
};

function DealCard({ deal, stages, canMove, onMove }: { deal: Deal; stages: Stage[]; canMove: boolean; onMove: (stageId: string) => void }) {
  const overdue = deal.status === "open" && deal.expected_close_date && new Date(deal.expected_close_date) < new Date();
  return (
    <div className="group rounded-lg border bg-card p-3 shadow-xs transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <Link href={`/deals/${deal.id}`} className="text-sm leading-snug font-medium hover:underline" draggable={false}>
          {deal.name}
        </Link>
        {canMove && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-xs" className="-mt-1 -mr-1 opacity-60 group-hover:opacity-100" aria-label="Move deal">
                <MoreVertical />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Move to</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {stages
                .filter((stage) => stage.id !== deal.stage.id)
                .map((stage) => (
                  <DropdownMenuItem key={stage.id} onClick={() => onMove(stage.id)}>
                    {stage.name}
                  </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      {deal.company && <p className="mt-0.5 truncate text-xs text-muted-foreground">{deal.company.name}</p>}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-sm font-semibold tabular-nums">{formatCurrency(deal.value, deal.currency)}</span>
        {deal.owner && <UserAvatar name={deal.owner.full_name} className="size-6" />}
      </div>
      {deal.expected_close_date && (
        <p className={`mt-2 flex items-center gap-1 text-xs ${overdue ? "text-rose-600" : "text-muted-foreground"}`}>
          <CalendarDays className="size-3" /> {formatDate(deal.expected_close_date)}
        </p>
      )}
    </div>
  );
}

export function PipelineView() {
  const [formOpen, setFormOpen] = useState(false);
  const { canEdit } = useCurrentUser();
  const list = useListState({ filters: ["owner_id"] });
  const { data: board, isLoading, error, refetch } = useDealBoard({ search: list.search || undefined, owner_id: list.filters.owner_id || undefined });
  const { data: users = [] } = useUsers();
  const move = useMoveDeal();

  const stages = board?.columns.map((column) => column.stage) ?? [];
  const openValue = board?.columns.filter((c) => c.stage.stage_type === "open").reduce((sum, c) => sum + c.total_value, 0) ?? 0;

  return (
    <>
      <PageHeader
        title="Pipeline"
        description={board ? `${formatCurrency(openValue)} in open deals. Drag cards between stages to update them.` : "Your sales pipeline."}
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus /> New deal
          </Button>
        }
      />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search deals…" />
        <FilterSelect
          value={list.filters.owner_id}
          onChange={(v) => list.setFilter("owner_id", v)}
          placeholder="All owners"
          options={users.map((u) => ({ value: u.id, label: u.full_name }))}
        />
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : isLoading || !board ? (
        <div className="flex gap-3 overflow-hidden">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-96 w-72 shrink-0" />
          ))}
        </div>
      ) : (
        <KanbanBoard<Deal>
          columns={board.columns.map((column) => ({
            id: column.stage.id,
            accent: ACCENTS[column.stage.stage_type],
            title: (
              <>
                <span>{column.stage.name}</span>
                <span className="rounded-full bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground">{column.count}</span>
              </>
            ),
            subtitle: `${formatCurrency(column.total_value, "USD", true)} · ${column.stage.probability}%`,
            items: column.deals,
          }))}
          canDrag={(deal) => canEdit(deal)}
          onMove={(dealId, stageId) => move.mutate({ dealId, stageId })}
          renderCard={(deal) => (
            <DealCard deal={deal} stages={stages} canMove={canEdit(deal)} onMove={(stageId) => move.mutate({ dealId: deal.id, stageId })} />
          )}
        />
      )}

      <DealFormDialog open={formOpen} onOpenChange={setFormOpen} />
    </>
  );
}
