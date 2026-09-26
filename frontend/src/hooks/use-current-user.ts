"use client";

import { useQuery } from "@tanstack/react-query";

import { usersService } from "@/services/users";
import type { Profile } from "@/types";

export const currentUserKey = ["me"] as const;

/** The signed-in user's profile and role, plus simple permission helpers. */
export function useCurrentUser() {
  const query = useQuery({ queryKey: currentUserKey, queryFn: usersService.me, staleTime: 5 * 60_000 });
  const user = query.data;
  const isAdmin = user?.role === "admin";
  const isManager = isAdmin || user?.role === "manager";

  return {
    ...query,
    user,
    isAdmin,
    /** Admin or Manager. */
    isManager,
    /** Mirrors the backend rule: managers edit anything, reps edit what they own. */
    canEdit: (record: { owner?: { id: string } | null; owner_id?: string | null }) =>
      isManager || (user != null && (record.owner?.id ?? record.owner_id) === user.id),
  };
}

export function roleLabel(role: Profile["role"]) {
  return { admin: "Admin", manager: "Manager", sales_rep: "Sales Rep" }[role];
}
