"use client";

import { Handshake, KanbanSquare, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { DataTable, type Column } from "@/components/shared/data-table";
import { FilterSelect } from "@/components/shared/filter-select";
import { OwnerCell } from "@/components/shared/owner-cell";
import { Pagination } from "@/components/shared/pagination";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { useListState } from "@/hooks/use-list-state";
import { DEAL_STATUSES, type Deal } from "@/types";
import { formatCurrency, formatDate, humanize } from "@/utils/format";

import { DealFormDialog } from "./deal-form-dialog";
import { dealHooks, useDefaultPipeline } from "./hooks";

const columns: Column<Deal>[] = [
  {
    key: "name",
    header: "Deal",
    sortKey: "name",
    cell: (deal) => (
      <div className="min-w-0">
        <Link href={`/deals/${deal.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
          {deal.name}
        </Link>
        <p className="truncate text-xs text-muted-foreground">{deal.company?.name ?? deal.contact?.name ?? "—"}</p>
      </div>
    ),
  },
  {
    key: "value",
    header: "Value",
    sortKey: "value",
    className: "text-right",
    cell: (d) => <span className="font-medium tabular-nums">{formatCurrency(d.value, d.currency)}</span>,
  },
  {
    key: "stage",
    header: "Stage",
    cell: (d) => (d.status === "open" ? <StatusBadge value="open" label={d.stage.name} /> : <StatusBadge value={d.status} />),
  },
  { key: "probability", header: "Prob.", sortKey: "probability", cell: (d) => `${d.probability}%` },
  { key: "close", header: "Expected close", sortKey: "expected_close_date", cell: (d) => formatDate(d.expected_close_date) },
  { key: "owner", header: "Owner", cell: (d) => <OwnerCell owner={d.owner} /> },
];

export function DealsView() {
  const router = useRouter();
  const [formOpen, setFormOpen] = useState(false);
  const list = useListState({ filters: ["status", "stage_id", "owner_id"] });
  const { data, isLoading, error, refetch } = dealHooks.useList(list.params);
  const { pipeline } = useDefaultPipeline();
  const { data: users = [] } = useUsers();

  return (
    <>
      <PageHeader
        title="Deals"
        description="Every opportunity in your pipeline."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link href="/pipeline">
                <KanbanSquare /> Board view
              </Link>
            </Button>
            <Button onClick={() => setFormOpen(true)}>
              <Plus /> New deal
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search deals…" />
        <FilterSelect
          value={list.filters.status}
          onChange={(v) => list.setFilter("status", v)}
          placeholder="All statuses"
          options={DEAL_STATUSES.map((s) => ({ value: s, label: humanize(s) }))}
        />
        <FilterSelect
          value={list.filters.stage_id}
          onChange={(v) => list.setFilter("stage_id", v)}
          placeholder="All stages"
          options={(pipeline?.stages ?? []).map((s) => ({ value: s.id, label: s.name }))}
        />
        <FilterSelect
          value={list.filters.owner_id}
          onChange={(v) => list.setFilter("owner_id", v)}
          placeholder="All owners"
          options={users.map((u) => ({ value: u.id, label: u.full_name }))}
        />
        {list.hasActiveFilters && (
          <Button variant="ghost" onClick={list.clearFilters}>
            Clear filters
          </Button>
        )}
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={data?.items}
            isLoading={isLoading}
            sortBy={list.sortBy}
            sortOrder={list.sortOrder}
            onSort={list.setSort}
            onRowClick={(deal) => router.push(`/deals/${deal.id}`)}
            empty={
              <EmptyState
                icon={Handshake}
                title={list.hasActiveFilters ? "No deals match your filters" : "No deals yet"}
                description={list.hasActiveFilters ? "Try a different search or clear the filters." : "Create a deal or convert a lead."}
              />
            }
          />
          {data && (
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />
          )}
        </>
      )}

      <DealFormDialog open={formOpen} onOpenChange={setFormOpen} onSaved={(d) => router.push(`/deals/${d.id}`)} />
    </>
  );
}
