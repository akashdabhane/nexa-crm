"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
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
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { useListState } from "@/hooks/use-list-state";
import { companiesService } from "@/services/companies";
import type { Company } from "@/types";
import { formatDate, formatNumber } from "@/utils/format";

import { CompanyFormDialog } from "./company-form-dialog";
import { companyHooks } from "./hooks";

const columns: Column<Company>[] = [
  {
    key: "name",
    header: "Company",
    sortKey: "name",
    cell: (company) => (
      <div className="min-w-0">
        <Link href={`/companies/${company.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
          {company.name}
        </Link>
        {company.website && <p className="truncate text-xs text-muted-foreground">{company.website}</p>}
      </div>
    ),
  },
  { key: "industry", header: "Industry", sortKey: "industry", cell: (c) => c.industry ?? "—" },
  { key: "city", header: "Location", sortKey: "city", cell: (c) => [c.city, c.country].filter(Boolean).join(", ") || "—" },
  { key: "employees", header: "Employees", sortKey: "employee_count", cell: (c) => formatNumber(c.employee_count) },
  { key: "contacts", header: "Contacts", cell: (c) => c.contact_count },
  { key: "owner", header: "Owner", cell: (c) => <OwnerCell owner={c.owner} /> },
  { key: "created", header: "Created", sortKey: "created_at", cell: (c) => formatDate(c.created_at) },
];

export function CompaniesView() {
  const router = useRouter();
  const [formOpen, setFormOpen] = useState(false);
  const list = useListState({ filters: ["industry", "owner_id"], defaultSort: "name", defaultOrder: "asc" });
  const { data, isLoading, error, refetch } = companyHooks.useList(list.params);
  const { data: industries = [] } = useQuery({ queryKey: ["companies", "industries"], queryFn: companiesService.industries });
  const { data: users = [] } = useUsers();

  return (
    <>
      <PageHeader
        title="Companies"
        description="Organizations you do business with."
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus /> New company
          </Button>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search name, industry, city…" />
        <FilterSelect
          value={list.filters.industry}
          onChange={(v) => list.setFilter("industry", v)}
          placeholder="All industries"
          options={industries.map((i) => ({ value: i, label: i }))}
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
            onRowClick={(company) => router.push(`/companies/${company.id}`)}
            empty={
              <EmptyState
                icon={Building2}
                title={list.hasActiveFilters ? "No companies match your filters" : "No companies yet"}
                description={list.hasActiveFilters ? "Try a different search or clear the filters." : "Add the first organization you work with."}
              />
            }
          />
          {data && (
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />
          )}
        </>
      )}

      <CompanyFormDialog open={formOpen} onOpenChange={setFormOpen} onSaved={(c) => router.push(`/companies/${c.id}`)} />
    </>
  );
}
