"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";

export type KanbanColumn<T> = {
  id: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  accent?: string;
  items: T[];
};

type KanbanBoardProps<T extends { id: string }> = {
  columns: KanbanColumn<T>[];
  renderCard: (item: T) => React.ReactNode;
  /** Called when a card is dropped on a different column. */
  onMove: (itemId: string, toColumnId: string) => void;
  canDrag?: (item: T) => boolean;
};

/**
 * Horizontal board with drag-and-drop between columns, built on the native
 * HTML5 drag-and-drop API (no extra library needed).
 */
export function KanbanBoard<T extends { id: string }>({ columns, renderCard, onMove, canDrag }: KanbanBoardProps<T>) {
  const [dragging, setDragging] = useState<{ itemId: string; fromColumn: string } | null>(null);
  const [overColumn, setOverColumn] = useState<string | null>(null);

  return (
    <div className="-mx-4 overflow-x-auto px-4 pb-4 md:-mx-6 md:px-6">
      <div className="flex min-h-[60vh] gap-3">
        {columns.map((column) => {
          const isTarget = dragging && overColumn === column.id && dragging.fromColumn !== column.id;
          return (
            <section
              key={column.id}
              aria-label={typeof column.title === "string" ? column.title : undefined}
              onDragOver={(event) => {
                if (!dragging) return;
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                setOverColumn(column.id);
              }}
              onDragLeave={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node)) setOverColumn(null);
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (dragging && dragging.fromColumn !== column.id) onMove(dragging.itemId, column.id);
                setDragging(null);
                setOverColumn(null);
              }}
              className={cn(
                "flex w-72 shrink-0 flex-col rounded-xl border bg-muted/40 transition-colors",
                isTarget && "border-primary bg-primary/5 ring-2 ring-primary/20",
              )}
            >
              <header className={cn("space-y-0.5 border-b border-t-4 px-3 py-2.5 rounded-t-xl", column.accent ?? "border-t-primary")}>
                <div className="flex items-center justify-between gap-2 text-sm font-semibold">{column.title}</div>
                {column.subtitle && <div className="text-xs text-muted-foreground">{column.subtitle}</div>}
              </header>
              <div className="flex flex-1 flex-col gap-2 p-2">
                {column.items.map((item) => {
                  const draggable = canDrag ? canDrag(item) : true;
                  return (
                    <div
                      key={item.id}
                      draggable={draggable}
                      onDragStart={(event) => {
                        event.dataTransfer.effectAllowed = "move";
                        event.dataTransfer.setData("text/plain", item.id);
                        setDragging({ itemId: item.id, fromColumn: column.id });
                      }}
                      onDragEnd={() => {
                        setDragging(null);
                        setOverColumn(null);
                      }}
                      className={cn(
                        draggable && "cursor-grab active:cursor-grabbing",
                        dragging?.itemId === item.id && "opacity-40",
                      )}
                    >
                      {renderCard(item)}
                    </div>
                  );
                })}
                {column.items.length === 0 && (
                  <p className="rounded-lg border border-dashed py-6 text-center text-xs text-muted-foreground">Drop deals here</p>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
