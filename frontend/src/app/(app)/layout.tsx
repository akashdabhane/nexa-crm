import type { Metadata } from "next";
import { cookies } from "next/headers";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { Topbar } from "@/components/layout/topbar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { OrganizationGate } from "@/features/organizations/organization-gate";

// The CRM is private (behind login): keep every page under this layout out of search results.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function AppLayout({ children }: LayoutProps<"/">) {
  // Remember whether the sidebar was collapsed (cookie written by the shadcn sidebar).
  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get("sidebar_state")?.value !== "false";

  // Nothing renders until an organization the user belongs to is selected.
  return (
    <OrganizationGate>
      <SidebarProvider defaultOpen={defaultOpen}>
        <AppSidebar />
        <SidebarInset className="min-w-0">
          <Topbar />
          <main className="flex-1 space-y-6 p-4 md:p-6">{children}</main>
        </SidebarInset>
      </SidebarProvider>
    </OrganizationGate>
  );
}
