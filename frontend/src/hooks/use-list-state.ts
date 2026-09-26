"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import type { ListParams, SortOrder } from "@/types";

/**
 * List-page state (page, search, sort, filters) stored in the URL query string,
 * so filtered views survive a refresh and can be shared as links.
 */
export function useListState<F extends string>({
  filters = [] as F[],
  defaultSort = "created_at",
  defaultOrder = "desc",
  pageSize = 20,
}: {
  filters?: F[];
  defaultSort?: string;
  defaultOrder?: SortOrder;
  pageSize?: number;
} = {}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const page = Number(searchParams.get("page") ?? 1) || 1;
  const search = searchParams.get("search") ?? "";
  const sortBy = searchParams.get("sort_by") ?? defaultSort;
  const sortOrder = (searchParams.get("sort_order") as SortOrder | null) ?? defaultOrder;
  const filterKey = filters.join(",");
  const filterValues = useMemo(
    () =>
      Object.fromEntries(filterKey.split(",").filter(Boolean).map((name) => [name, searchParams.get(name) ?? ""])) as Record<
        F,
        string
      >,
    [filterKey, searchParams],
  );

  const update = useCallback(
    (changes: Record<string, string | number | null>, resetPage = true) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [name, value] of Object.entries(changes)) {
        if (value === null || value === "" || value === undefined) next.delete(name);
        else next.set(name, String(value));
      }
      if (resetPage && !("page" in changes)) next.delete("page");
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const params: ListParams = {
    page,
    page_size: pageSize,
    search: search || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    ...filterValues,
  };

  return {
    params,
    page,
    search,
    sortBy,
    sortOrder,
    filters: filterValues,
    hasActiveFilters: Boolean(search) || Object.values<string>(filterValues).some(Boolean),
    setPage: (value: number) => update({ page: value > 1 ? value : null }, false),
    setSearch: (value: string) => update({ search: value }),
    setFilter: (name: F, value: string) => update({ [name]: value }),
    /** Change several filters in one URL update. */
    setFilters: (changes: Partial<Record<F, string>>) => update(changes as Record<string, string>),
    setSort: (column: string) =>
      update({
        sort_by: column,
        // Clicking the active column flips direction; a new column starts ascending.
        sort_order: column === sortBy ? (sortOrder === "asc" ? "desc" : "asc") : "asc",
      }),
    setSortTo: (column: string, order: SortOrder) => update({ sort_by: column, sort_order: order }),
    clearFilters: () => update(Object.fromEntries(["search", ...filters].map((name) => [name, null]))),
  };
}
