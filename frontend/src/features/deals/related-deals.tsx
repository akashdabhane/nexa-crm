"use client";

import { Handshake, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { EntityRef } from "@/types";
import { formatCurrency, formatDate } from "@/utils/format";

import { DealFormDialog } from "./deal-form-dialog";
import { dealHooks } from "./hooks";

/** Deals of a company or contact, with a shortcut to create one pre-linked. */
export function RelatedDeals({ filter, company, contact }: { filter: Record<string, string>; company?: EntityRef | null; contact?: EntityRef | null }) {
  const [adding, setAdding] = useState(false);
  const { data, isLoading } = dealHooks.useList({ ...filter, page_size: 50 });

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
          <Plus /> Add deal
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data?.items.length ? (
        <ul className="divide-y rounded-lg border">
          {data.items.map((deal) => (
            <li key={deal.id} className="flex items-center gap-3 p-3">
              <div className="min-w-0 flex-1">
                <Link href={`/deals/${deal.id}`} className="font-medium hover:underline">
                  {deal.name}
                </Link>
                <p className="text-xs text-muted-foreground">
                  {deal.stage.name} · close {formatDate(deal.expected_close_date)}
                </p>
              </div>
              <span className="text-sm font-medium tabular-nums">{formatCurrency(deal.value, deal.currency)}</span>
              <StatusBadge value={deal.status} />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState icon={Handshake} title="No deals yet" />
      )}
      <DealFormDialog open={adding} onOpenChange={setAdding} defaults={{ company, contact }} />
    </div>
  );
}
