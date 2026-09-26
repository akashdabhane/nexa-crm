import type { Metadata } from "next";
import { Suspense } from "react";

import { ActivitiesView } from "@/features/activities/activities-view";

export const metadata: Metadata = { title: "Activities" };

export default function ActivitiesPage() {
  return (
    <Suspense>
      <ActivitiesView />
    </Suspense>
  );
}
