"use client";

import { RecordTabs } from "@/components/shared/record-tabs";
import { NotesPanel } from "@/features/activities/notes-panel";
import { RecordTimeline } from "@/features/activities/record-timeline";
import type { Lead } from "@/types";

export function LeadTabs({ lead }: { lead: Lead }) {
  const links = { lead_id: lead.id };
  return (
    <RecordTabs
      tabs={[
        { value: "timeline", label: "Timeline", content: <RecordTimeline links={links} self="lead" /> },
        { value: "notes", label: "Notes", content: <NotesPanel filter={links} attachTo={links} /> },
      ]}
    />
  );
}
