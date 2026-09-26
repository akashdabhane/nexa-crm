import { cn } from "@/lib/utils";

/** Lead score 0–100 as a small colored bar. */
export function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-slate-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${score}%` }} />
      </div>
      <span className="w-7 text-xs tabular-nums text-muted-foreground">{score}</span>
    </div>
  );
}
