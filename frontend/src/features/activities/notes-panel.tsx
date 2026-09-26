"use client";

import { Pencil, StickyNote, Trash2 } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/states";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useCurrentUser } from "@/hooks/use-current-user";
import type { Note, RecordLinks } from "@/types";
import { formatDateTime } from "@/utils/format";

import { noteHooks } from "./hooks";

function NoteCard({ note }: { note: Note }) {
  const { canEdit } = useCurrentUser();
  const update = noteHooks.useUpdate();
  const remove = noteHooks.useDelete();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(note.body);

  return (
    <div className="group rounded-lg border p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <UserAvatar name={note.owner?.full_name ?? "?"} className="size-5" />
          <span className="font-medium text-foreground">{note.owner?.full_name ?? "Someone"}</span>
          <span>{formatDateTime(note.created_at)}</span>
          {note.updated_at !== note.created_at && <span>(edited)</span>}
        </div>
        {canEdit(note) && !editing && (
          <div className="flex opacity-0 group-hover:opacity-100 focus-within:opacity-100">
            <Button variant="ghost" size="icon-xs" onClick={() => setEditing(true)} aria-label="Edit note">
              <Pencil />
            </Button>
            <Button variant="ghost" size="icon-xs" onClick={() => remove.mutate(note.id)} aria-label="Delete note">
              <Trash2 />
            </Button>
          </div>
        )}
      </div>
      {editing ? (
        <div className="space-y-2">
          <Textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!text.trim() || update.isPending}
              onClick={() => update.mutate({ id: note.id, data: { body: text.trim() } }, { onSuccess: () => setEditing(false) })}
            >
              Save
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-line">{note.body}</p>
      )}
    </div>
  );
}

/** Notes tab: every note on a record, editable by its author (or a manager). */
export function NotesPanel({ filter, attachTo }: { filter: RecordLinks; attachTo: RecordLinks }) {
  const { data, isLoading } = noteHooks.useList({ ...(filter as Record<string, string>), page_size: 100 });
  const create = noteHooks.useCreate();
  const [text, setText] = useState("");

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Textarea rows={3} placeholder="Write a note…" value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex justify-end">
          <Button
            size="sm"
            disabled={!text.trim() || create.isPending}
            onClick={() => create.mutate({ body: text.trim(), ...attachTo }, { onSuccess: () => setText("") })}
          >
            Add note
          </Button>
        </div>
      </div>
      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data?.items.length ? (
        data.items.map((note) => <NoteCard key={note.id} note={note} />)
      ) : (
        <EmptyState icon={StickyNote} title="No notes yet" />
      )}
    </div>
  );
}
