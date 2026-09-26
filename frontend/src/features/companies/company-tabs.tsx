"use client";

import { RecordTabs } from "@/components/shared/record-tabs";
import { NotesPanel } from "@/features/activities/notes-panel";
import { RecordTimeline } from "@/features/activities/record-timeline";
import { RelatedContacts } from "@/features/contacts/related-contacts";
import { RelatedDeals } from "@/features/deals/related-deals";
import { RecordTasks } from "@/features/tasks/record-tasks";
import type { Company } from "@/types";

export function CompanyTabs({ company }: { company: Company }) {
  const ref = { id: company.id, name: company.name };
  const links = { company_id: company.id };
  return (
    <RecordTabs
      tabs={[
        { value: "timeline", label: "Timeline", content: <RecordTimeline links={links} self="company" /> },
        { value: "contacts", label: `Contacts (${company.contact_count})`, content: <RelatedContacts company={ref} /> },
        { value: "deals", label: `Deals (${company.deal_count})`, content: <RelatedDeals filter={links} company={ref} /> },
        { value: "tasks", label: "Tasks", content: <RecordTasks filter={links} defaults={{ company: ref }} /> },
        { value: "notes", label: "Notes", content: <NotesPanel filter={links} attachTo={links} /> },
      ]}
    />
  );
}
