"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Users } from "lucide-react";
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
import { UserAvatar } from "@/components/shared/user-avatar";
import { useUsers } from "@/components/shared/user-select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useListState } from "@/hooks/use-list-state";
import { contactsService } from "@/services/contacts";
import { CONTACT_STATUSES, type Contact } from "@/types";
import { formatDate, humanize } from "@/utils/format";

import { ContactFormDialog } from "./contact-form-dialog";
import { contactHooks } from "./hooks";

const columns: Column<Contact>[] = [
  {
    key: "name",
    header: "Name",
    sortKey: "first_name",
    cell: (contact) => (
      <div className="flex min-w-0 items-center gap-3">
        <UserAvatar name={contact.full_name} className="size-8" />
        <div className="min-w-0">
          <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
            {contact.full_name}
          </Link>
          <p className="truncate text-xs text-muted-foreground">{contact.email ?? "No email"}</p>
        </div>
      </div>
    ),
  },
  {
    key: "company",
    header: "Company",
    cell: (contact) =>
      contact.company ? (
        <div className="min-w-0">
          <Link href={`/companies/${contact.company.id}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>
            {contact.company.name}
          </Link>
          {contact.job_title && <p className="truncate text-xs text-muted-foreground">{contact.job_title}</p>}
        </div>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  { key: "phone", header: "Phone", cell: (c) => c.phone ?? "—" },
  { key: "status", header: "Status", sortKey: "status", cell: (c) => <StatusBadge value={c.status} /> },
  {
    key: "tags",
    header: "Tags",
    cell: (c) => (
      <div className="flex max-w-48 flex-wrap gap-1">
        {c.tags.slice(0, 3).map((tag) => (
          <Badge key={tag} variant="secondary" className="font-normal">
            {tag}
          </Badge>
        ))}
        {c.tags.length > 3 && <span className="text-xs text-muted-foreground">+{c.tags.length - 3}</span>}
      </div>
    ),
  },
  { key: "owner", header: "Owner", cell: (c) => <OwnerCell owner={c.owner} /> },
  { key: "created", header: "Created", sortKey: "created_at", cell: (c) => formatDate(c.created_at) },
];

export function ContactsView() {
  const router = useRouter();
  const [formOpen, setFormOpen] = useState(false);
  const list = useListState({ filters: ["status", "owner_id", "tag"] });
  const { data, isLoading, error, refetch } = contactHooks.useList(list.params);
  const { data: tags = [] } = useQuery({ queryKey: ["contacts", "tags"], queryFn: contactsService.tags });
  const { data: users = [] } = useUsers();

  return (
    <>
      <PageHeader
        title="Contacts"
        description="Everyone you're in touch with."
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus /> New contact
          </Button>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <SearchInput value={list.search} onChange={list.setSearch} placeholder="Search name, email, phone…" />
        <FilterSelect
          value={list.filters.status}
          onChange={(v) => list.setFilter("status", v)}
          placeholder="All statuses"
          options={CONTACT_STATUSES.map((s) => ({ value: s, label: humanize(s) }))}
        />
        <FilterSelect
          value={list.filters.tag}
          onChange={(v) => list.setFilter("tag", v)}
          placeholder="All tags"
          options={tags.map((t) => ({ value: t, label: t }))}
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
            onRowClick={(contact) => router.push(`/contacts/${contact.id}`)}
            empty={
              <EmptyState
                icon={Users}
                title={list.hasActiveFilters ? "No contacts match your filters" : "No contacts yet"}
                description={list.hasActiveFilters ? "Try a different search or clear the filters." : "Add your first contact to get started."}
              />
            }
          />
          {data && (
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={list.setPage} />
          )}
        </>
      )}

      <ContactFormDialog open={formOpen} onOpenChange={setFormOpen} onSaved={(c) => router.push(`/contacts/${c.id}`)} />
    </>
  );
}
