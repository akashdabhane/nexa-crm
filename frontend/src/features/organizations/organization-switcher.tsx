"use client";

import { Building2, Check, ChevronsUpDown, LayoutGrid } from "lucide-react";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import { roleLabel } from "@/hooks/use-current-user";
import { enterOrganization } from "@/lib/active-organization";

import { useMyOrganizations } from "./hooks";
import { useCurrentOrganization } from "./organization-gate";

/** Sidebar control showing the current organization; lists only the user's own organizations. */
export function OrganizationSwitcher() {
  const current = useCurrentOrganization();
  const { data: organizations = [] } = useMyOrganizations();
  const others = organizations.filter((org) => org.id !== current.id && org.status === "active");

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              tooltip={current.name}
              className="border bg-background data-[state=open]:bg-sidebar-accent"
              aria-label={`Organization: ${current.name}. Switch organization`}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Building2 className="size-4" />
              </span>
              <span className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{current.name}</span>
                <span className="truncate text-xs text-muted-foreground">{roleLabel(current.role)}</span>
              </span>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-60">
            <DropdownMenuLabel className="text-xs text-muted-foreground">Organizations</DropdownMenuLabel>
            <DropdownMenuItem disabled className="opacity-100">
              <Check /> <span className="truncate">{current.name}</span>
            </DropdownMenuItem>
            {others.map((org) => (
              <DropdownMenuItem key={org.id} onClick={() => enterOrganization(org.id)}>
                <span className="size-4" /> <span className="truncate">{org.name}</span>
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/organizations">
                <LayoutGrid /> All organizations
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
