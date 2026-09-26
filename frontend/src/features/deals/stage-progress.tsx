"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Deal, Stage } from "@/types";

/**
 * Clickable stage path (New → … → Won / Lost) at the top of a deal page.
 * Clicking a stage moves the deal there.
 */
export function StageProgress({
  deal,
  stages,
  disabled,
  onMove,
}: {
  deal: Deal;
  stages: Stage[];
  disabled?: boolean;
  onMove: (stage: Stage) => void;
}) {
  const current = stages.findIndex((stage) => stage.id === deal.stage.id);

  return (
    <div className="flex overflow-x-auto rounded-xl border bg-card p-1">
      {stages.map((stage, index) => {
        const isCurrent = index === current;
        const isPast = deal.status === "open" && stage.stage_type === "open" && index < current;
        const tone =
          isCurrent && stage.stage_type === "won"
            ? "bg-emerald-600 text-white"
            : isCurrent && stage.stage_type === "lost"
              ? "bg-rose-600 text-white"
              : isCurrent
                ? "bg-primary text-primary-foreground"
                : isPast
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted";
        return (
          <button
            key={stage.id}
            type="button"
            disabled={disabled || isCurrent}
            onClick={() => onMove(stage)}
            className={cn(
              "flex min-w-24 flex-1 items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors disabled:cursor-default",
              tone,
            )}
          >
            {isPast && <Check className="size-3" />}
            {stage.name}
          </button>
        );
      })}
    </div>
  );
}
