import type { Metadata } from "next";
import { Suspense } from "react";

import { DealsView } from "@/features/deals/deals-view";

export const metadata: Metadata = { title: "Deals" };

export default function DealsPage() {
  return (
    <Suspense>
      <DealsView />
    </Suspense>
  );
}
