import type { Metadata } from "next";

import { OrganizationsView } from "@/features/organizations/organizations-view";

export const metadata: Metadata = { title: "Your organizations", robots: { index: false, follow: false } };

export default function OrganizationsPage() {
  return <OrganizationsView />;
}
