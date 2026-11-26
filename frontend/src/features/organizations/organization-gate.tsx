"use client";

import { createContext, useContext, useEffect, useSyncExternalStore } from "react";

import { LogoMark } from "@/components/layout/logo";
import { leaveToOrganizationPicker } from "@/lib/active-organization";
import type { MyOrganization } from "@/types";

import { useActiveOrganizationId, useMyOrganizations } from "./hooks";

const OrganizationContext = createContext<MyOrganization | null>(null);

/** The organization the CRM pages are showing. Only usable inside `OrganizationGate`. */
export function useCurrentOrganization(): MyOrganization {
  const organization = useContext(OrganizationContext);
  if (!organization) throw new Error("useCurrentOrganization must be used inside OrganizationGate");
  return organization;
}

const noSubscription = () => () => {};

/**
 * Renders the CRM only once an organization you're an active member of is selected;
 * otherwise sends you to the organization picker. (The API enforces this too; this
 * just avoids rendering pages that can't load.)
 */
export function OrganizationGate({ children }: { children: React.ReactNode }) {
  const hydrated = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
  const activeId = useActiveOrganizationId();
  const organizations = useMyOrganizations();
  const current = organizations.data?.find((org) => org.id === activeId && org.status === "active") ?? null;

  useEffect(() => {
    if (!hydrated) return;
    if (!activeId || (organizations.data && !current)) leaveToOrganizationPicker();
  }, [hydrated, activeId, organizations.data, current]);

  if (!current) {
    return (
      <div className="flex min-h-svh items-center justify-center" aria-busy="true" aria-label="Loading organization">
        <LogoMark className="size-10 animate-pulse" />
      </div>
    );
  }
  return <OrganizationContext.Provider value={current}>{children}</OrganizationContext.Provider>;
}
