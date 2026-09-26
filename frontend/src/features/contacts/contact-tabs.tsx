"use client";

import { RecordTabs } from "@/components/shared/record-tabs";
import { NotesPanel } from "@/features/activities/notes-panel";
import { RecordTimeline } from "@/features/activities/record-timeline";
import { RelatedDeals } from "@/features/deals/related-deals";
import { RecordTasks } from "@/features/tasks/record-tasks";
import type { Contact } from "@/types";

export function ContactTabs({ contact }: { contact: Contact }) {
  const ref = { id: contact.id, name: contact.full_name };
  const attachTo = { contact_id: contact.id, company_id: contact.company?.id ?? null };
  return (
    <RecordTabs
      tabs={[
        {
          value: "timeline",
          label: "Timeline",
          content: <RecordTimeline links={{ contact_id: contact.id }} attachTo={attachTo} self="contact" />,
        },
        {
          value: "deals",
          label: "Deals",
          content: <RelatedDeals filter={{ contact_id: contact.id }} contact={ref} company={contact.company} />,
        },
        {
          value: "tasks",
          label: "Tasks",
          content: <RecordTasks filter={{ contact_id: contact.id }} defaults={{ contact: ref, company: contact.company }} />,
        },
        { value: "notes", label: "Notes", content: <NotesPanel filter={{ contact_id: contact.id }} attachTo={attachTo} /> },
      ]}
    />
  );
}
