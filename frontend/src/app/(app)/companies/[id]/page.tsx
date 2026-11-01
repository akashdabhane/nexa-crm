import type { Metadata } from "next";

import { CompanyDetail } from "@/features/companies/company-detail";

export const metadata: Metadata = { title: "Company" };

export default async function CompanyPage({ params }: PageProps<"/companies/[id]">) {
  const { id } = await params;
  return <CompanyDetail id={id} />;
}
