"use client";

import { Plus, Target } from "lucide-react";
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
import { LEAD_SOURCES, LEAD_STATUSES, type Lead } from "@/types";
import { formatDate, humanize } from "@/utils/format";

import { leadHooks } from "./hooks";
import { LeadFormDialog } from "./lead-form-dialog";
import { ScoreBar } from "./score-bar";

const columns: Column<Lead>[] = [
  {
    key: "name",
    header: "Lead",
    sortKey: "name",
    cell: (lead) => (
      <div className="min-w-0">
        <Link href={`/leads/${lead.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
          {lead.name}
        </Link>
        <p className="truncate text-xs text-muted-foreground">{lead.email ?? lead.phone ?? "—"}</p>
      </div>
    ),
  },
  { key: "company", header: "Company", cell: (l) => l.company_name ?? "—" },
  { key: "source", header: "Source", sortKey: "source", cell: (l) => humanize(l.source) },
  { key: "status", header: "Status", sortKey: "status", cell: (l) => <StatusBadge value={l.status} /> },
  { key: "score", header: "Score", sortKey: "score", cell: (l) => <ScoreBar score={l.score} /> },
  { key: "owner", header: "Owner", cell: (l) => <OwnerCell owner={l.owner} /> },
  { key: "created", header: "Created", sortKey: "created_at", cell: (l) => formatDate(l.created_at) },
];

export function LeadsView() {
  const router = useRouter();
  const [formOpen, setFormOpen] = useState(false);
  const list = useListState({ filters: ["status", "source", "owner_id"] });
  const { data, isLoading, error, refetch } = leadHooks.useList(list.params);
  const { data: users = [] } = useUsers();

  return (
    <>
      <PageHeader
        title="Leads"
        description="Prospects to qualify and convert into customers."
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus /> New lead
          </Button>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search name, email, company…" />
        <FilterSelect
          value={list.filters.status}
          onChange={(v) => list.setFilter("status", v)}
          placeholder="All statuses"
          options={LEAD_STATUSES.map((s) => ({ value: s, label: humanize(s) }))}
        />
        <FilterSelect
          value={list.filters.source}
          onChange={(v) => list.setFilter("source", v)}
          placeholder="All sources"
          options={LEAD_SOURCES.map((s) => ({ value: s, label: humanize(s) }))}
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
            onRowClick={(lead) => router.push(`/leads/${lead.id}`)}
            empty={
              <EmptyState
                icon={Target}
                title={list.hasActiveFilters ? "No leads match your filters" : "No leads yet"}
                description={list.hasActiveFilters ? "Try a different search or clear the filters." : "Capture your first prospect."}
              />
            }
          />
          {data && (
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />
          )}
        </>
      )}

      <LeadFormDialog open={formOpen} onOpenChange={setFormOpen} onSaved={(l) => router.push(`/leads/${l.id}`)} />
    </>
  );
}
