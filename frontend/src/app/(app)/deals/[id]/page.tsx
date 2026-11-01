import type { Metadata } from "next";

import { DealDetail } from "@/features/deals/deal-detail";

export const metadata: Metadata = { title: "Deal" };

export default async function DealPage({ params }: PageProps<"/deals/[id]">) {
  const { id } = await params;
  return <DealDetail id={id} />;
}
