"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { FilterSelect } from "@/components/shared/filter-select";
import { Pagination } from "@/components/shared/pagination";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { useUsers } from "@/components/shared/user-select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { auditService, entityHref } from "@/services/notifications";
import type { AuditLog } from "@/types";
import { formatDateTime, humanize } from "@/utils/format";

const ENTITY_TYPES = ["company", "contact", "lead", "deal"];

function describe(log: AuditLog) {
  const { details } = log;
  if (log.action.endsWith("stage_changed")) return `${details.from} → ${details.to}`;
  if (details.changes) {
    return Object.entries(details.changes)
      .map(([field, [from, to]]) => `${humanize(field)}: ${from ?? "—"} → ${to ?? "—"}`)
      .join("; ");
  }
  return null;
}

export function AuditLogSettings() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [entityType, setEntityType] = useState("");
  const [userId, setUserId] = useState("");
  const params = { page, page_size: 25, search: search || undefined, entity_type: entityType || undefined, user_id: userId || undefined };
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["audit", params],
    queryFn: () => auditService.list(params),
    placeholderData: keepPreviousData,
  });
  const { data: users = [] } = useUsers();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit log</CardTitle>
        <CardDescription>Who created, changed, converted or deleted records, and when.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <SearchInput
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
            placeholder="Search action or record…"
          />
          <FilterSelect
            value={entityType}
            onChange={(v) => {
              setEntityType(v);
              setPage(1);
            }}
            placeholder="All records"
            options={ENTITY_TYPES.map((t) => ({ value: t, label: humanize(t) }))}
          />
          <FilterSelect
            value={userId}
            onChange={(v) => {
              setUserId(v);
              setPage(1);
            }}
            placeholder="All users"
            options={users.map((u) => ({ value: u.id, label: u.full_name }))}
          />
        </div>
        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : isLoading || !data ? (
          <Skeleton className="h-64" />
        ) : data.items.length === 0 ? (
          <EmptyState title="No audit entries" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Record</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((log) => {
                  const href = log.action.endsWith("deleted") ? null : entityHref(log.entity_type, log.entity_id);
                  return (
                    <TableRow key={log.id}>
                      <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                      <TableCell className="whitespace-nowrap">{log.user?.full_name ?? "System"}</TableCell>
                      <TableCell className="whitespace-nowrap font-mono text-xs">{log.action}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {href ? (
                          <Link href={href} className="text-primary hover:underline">
                            {log.details.name ?? humanize(log.entity_type)}
                          </Link>
                        ) : (
                          (log.details.name ?? humanize(log.entity_type))
                        )}
                      </TableCell>
                      <TableCell className="max-w-md truncate text-xs text-muted-foreground" title={describe(log) ?? undefined}>
                        {describe(log) ?? "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
        {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />}
      </CardContent>
    </Card>
  );
}
