"use client";

import { Clock, Trash2 } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ACTIVITY_ICONS } from "@/features/activities/activity-icons";
import { cn } from "@/lib/utils";
import type { EntityRef, TimelineItem } from "@/types";
import { formatDateTime, formatRelative } from "@/utils/format";

type TimelineProps = {
  items: TimelineItem[];
  /** Hide the link back to the record whose page we are on. */
  hideLinks?: ("contact" | "company" | "lead" | "deal")[];
  canDelete?: (item: TimelineItem) => boolean;
  onDelete?: (item: TimelineItem) => void;
};

const LINK_PATHS = { contact: "/contacts", company: "/companies", lead: "/leads", deal: "/deals" } as const;

function RelatedLinks({ refs, hide }: { refs: Partial<Record<keyof typeof LINK_PATHS, EntityRef | null | undefined>>; hide: string[] }) {
  const links = (Object.keys(LINK_PATHS) as (keyof typeof LINK_PATHS)[])
    .filter((key) => refs[key] && !hide.includes(key))
    .map((key) => ({ key, ref: refs[key]!, href: `${LINK_PATHS[key]}/${refs[key]!.id}` }));
  if (links.length === 0) return null;
  return (
    <span className="text-muted-foreground">
      {" · "}
      {links.map((link, index) => (
        <span key={link.key}>
          {index > 0 && ", "}
          <Link href={link.href} className="hover:text-foreground hover:underline">
            {link.ref.name}
          </Link>
        </span>
      ))}
    </span>
  );
}

/** Chronological list of activities and notes (the "activity timeline"). */
export function ActivityTimeline({ items, hideLinks = [], canDelete, onDelete }: TimelineProps) {
  return (
    <ol className="relative space-y-5 before:absolute before:top-2 before:bottom-2 before:left-4 before:w-px before:bg-border">
      {items.map((item) => {
        const entry = item.kind === "activity" ? item.activity : item.note;
        const kind = item.kind === "activity" ? item.activity.type : "note";
        const { icon: Icon, className } = ACTIVITY_ICONS[kind];
        return (
          <li key={`${item.kind}-${entry.id}`} className="group relative flex gap-3">
            <span className={cn("relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full ring-4 ring-card", className)}>
              <Icon className="size-4" />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm">
                  <span className="font-medium">{item.kind === "activity" ? item.activity.subject : "Note"}</span>
                  <RelatedLinks refs={entry} hide={hideLinks} />
                </p>
                <div className="flex shrink-0 items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="text-xs text-muted-foreground">{formatRelative(item.occurred_at)}</span>
                    </TooltipTrigger>
                    <TooltipContent>{formatDateTime(item.occurred_at)}</TooltipContent>
                  </Tooltip>
                  {onDelete && canDelete?.(item) && (
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                      onClick={() => onDelete(item)}
                      aria-label="Delete"
                    >
                      <Trash2 />
                    </Button>
                  )}
                </div>
              </div>
              {item.kind === "activity" && item.activity.description && (
                <p className="mt-1 text-sm whitespace-pre-line text-muted-foreground">{item.activity.description}</p>
              )}
              {item.kind === "note" && (
                <p className="mt-1 rounded-lg bg-muted/60 p-3 text-sm whitespace-pre-line">{item.note.body}</p>
              )}
              <p className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                {entry.owner?.full_name ?? "Someone"}
                {item.kind === "activity" && item.activity.duration_minutes ? (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="size-3" /> {item.activity.duration_minutes} min
                  </span>
                ) : null}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
