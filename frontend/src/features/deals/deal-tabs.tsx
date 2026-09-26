"use client";

import { RecordTabs } from "@/components/shared/record-tabs";
import { NotesPanel } from "@/features/activities/notes-panel";
import { RecordTimeline } from "@/features/activities/record-timeline";
import { RecordTasks } from "@/features/tasks/record-tasks";
import type { Deal } from "@/types";

export function DealTabs({ deal }: { deal: Deal }) {
  const ref = { id: deal.id, name: deal.name };
  const attachTo = { deal_id: deal.id, contact_id: deal.contact?.id ?? null, company_id: deal.company?.id ?? null };
  return (
    <RecordTabs
      tabs={[
        { value: "timeline", label: "Timeline", content: <RecordTimeline links={{ deal_id: deal.id }} attachTo={attachTo} self="deal" /> },
        {
          value: "tasks",
          label: "Tasks",
          content: <RecordTasks filter={{ deal_id: deal.id }} defaults={{ deal: ref, contact: deal.contact, company: deal.company }} />,
        },
        { value: "notes", label: "Notes", content: <NotesPanel filter={{ deal_id: deal.id }} attachTo={attachTo} /> },
      ]}
    />
  );
}
