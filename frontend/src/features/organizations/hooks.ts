"use client";

import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";

import { getActiveOrganizationId } from "@/lib/active-organization";
import { organizationsService } from "@/services/organizations";

export const myOrganizationsKey = ["organizations", "mine"] as const;
export const myInvitationsKey = ["organizations", "my-invitations"] as const;

/** Organizations the signed-in user belongs to (never anyone else's). */
export function useMyOrganizations() {
  return useQuery({ queryKey: myOrganizationsKey, queryFn: organizationsService.mine, staleTime: 60_000 });
}

const noSubscription = () => () => {};

/** The remembered organization id (null during server rendering and before one is chosen). */
export function useActiveOrganizationId() {
  return useSyncExternalStore(noSubscription, getActiveOrganizationId, () => null);
}

export function useMyInvitations() {
  return useQuery({ queryKey: myInvitationsKey, queryFn: organizationsService.myInvitations });
}
