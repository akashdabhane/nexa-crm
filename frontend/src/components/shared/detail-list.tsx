import { cn } from "@/lib/utils";

/** Label/value rows for the "Details" card on record pages. */
export function DetailList({ items, className }: { items: { label: string; value: React.ReactNode }[]; className?: string }) {
  return (
    <dl className={cn("divide-y text-sm", className)}>
      {items.map((item) => (
        <div key={item.label} className="grid grid-cols-5 gap-3 py-2.5 first:pt-0 last:pb-0">
          <dt className="col-span-2 text-muted-foreground">{item.label}</dt>
          <dd className="col-span-3 min-w-0 break-words">{item.value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
