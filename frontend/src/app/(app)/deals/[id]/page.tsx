import { DealDetail } from "@/features/deals/deal-detail";

export default async function DealPage({ params }: PageProps<"/deals/[id]">) {
  const { id } = await params;
  return <DealDetail id={id} />;
}
