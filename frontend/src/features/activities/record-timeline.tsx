"use client";

import { History, Plus, StickyNote } from "lucide-react";
import { useState } from "react";

import { ActivityTimeline } from "@/components/shared/activity-timeline";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useCurrentUser } from "@/hooks/use-current-user";
import type { RecordLinks, TimelineItem } from "@/types";

import { activityHooks, noteHooks, useTimeline } from "./hooks";
import { LogActivityDialog } from "./log-activity-dialog";

type LinkKey = "contact" | "company" | "lead" | "deal";

/**
 * Timeline tab on a record page: log activities, add notes, see history.
 * `links` selects the timeline (exactly one id); `attachTo` is what new entries
 * link to, e.g. a contact's page also attaches its company.
 */
export function RecordTimeline({ links, attachTo = links, self }: { links: RecordLinks; attachTo?: RecordLinks; self: LinkKey }) {
  const { canEdit } = useCurrentUser();
  const { data: items, isLoading, error, refetch } = useTimeline(links);
  const addNote = noteHooks.useCreate();
  const deleteNote = noteHooks.useDelete();
  const deleteActivity = activityHooks.useDelete();
  const [logging, setLogging] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");

  function saveNote() {
    if (!noteText.trim()) return;
    addNote.mutate(
      { body: noteText.trim(), ...attachTo },
      {
        onSuccess: () => {
          setNoteText("");
          setNoteOpen(false);
        },
      },
    );
  }

  function remove(item: TimelineItem) {
    if (item.kind === "note") deleteNote.mutate(item.note.id);
    else deleteActivity.mutate(item.activity.id);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => setLogging(true)}>
          <Plus /> Log activity
        </Button>
        <Button size="sm" variant="outline" onClick={() => setNoteOpen((open) => !open)}>
          <StickyNote /> Add note
        </Button>
      </div>

      {noteOpen && (
        <div className="space-y-2 rounded-lg border p-3">
          <Textarea autoFocus rows={3} value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Write a note…" />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setNoteOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={saveNote} disabled={!noteText.trim() || addNote.isPending}>
              Save note
            </Button>
          </div>
        </div>
      )}

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : isLoading ? (
        <Skeleton className="h-40" />
      ) : items && items.length > 0 ? (
        <ActivityTimeline
          items={items}
          hideLinks={[self]}
          canDelete={(item) => canEdit(item.kind === "note" ? item.note : item.activity)}
          onDelete={remove}
        />
      ) : (
        <EmptyState icon={History} title="No activity yet" description="Log a call, meeting or email, or add a note." />
      )}

      <LogActivityDialog open={logging} onOpenChange={setLogging} links={attachTo} />
    </div>
  );
}
