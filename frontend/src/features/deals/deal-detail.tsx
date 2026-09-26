"use client";

import { Handshake } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { DetailList } from "@/components/shared/detail-list";
import { OwnerCell } from "@/components/shared/owner-cell";
import { RecordHeader } from "@/components/shared/record-header";
import { DetailSkeleton, ErrorState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { formatCurrency, formatDate, formatDateTime } from "@/utils/format";

import { DealFormDialog } from "./deal-form-dialog";
import { DealTabs } from "./deal-tabs";
import { dealHooks, useMoveDeal, usePipelines } from "./hooks";
import { StageProgress } from "./stage-progress";

export function DealDetail({ id }: { id: string }) {
  const router = useRouter();
  const { canEdit, isManager } = useCurrentUser();
  const { data: deal, isLoading, error, refetch } = dealHooks.useOne(id);
  const { data: pipelines = [] } = usePipelines();
  const move = useMoveDeal();
  const remove = dealHooks.useDelete();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (isLoading) return <DetailSkeleton />;
  if (error || !deal) return <ErrorState error={error} onRetry={refetch} />;

  const stages = pipelines.find((p) => p.id === deal.pipeline_id)?.stages ?? [];
  const editable = canEdit(deal);

  return (
    <>
      <RecordHeader
        backHref="/deals"
        backLabel="Deals"
        title={deal.name}
        avatar={
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Handshake className="size-6" />
          </div>
        }
        badges={<StatusBadge value={deal.status} />}
        subtitle={
          <span className="text-base font-semibold text-foreground">{formatCurrency(deal.value, deal.currency)}</span>
        }
        onEdit={editable ? () => setEditing(true) : undefined}
        onDelete={isManager ? () => setDeleting(true) : undefined}
      />

      {stages.length > 0 && (
        <StageProgress
          deal={deal}
          stages={stages}
          disabled={!editable || move.isPending}
          onMove={(stage) => move.mutate({ dealId: deal.id, stageId: stage.id })}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <DetailList
              items={[
                { label: "Stage", value: deal.stage.name },
                { label: "Probability", value: `${deal.probability}%` },
                {
                  label: "Weighted value",
                  value: formatCurrency((deal.value * deal.probability) / 100, deal.currency),
                },
                { label: "Expected close", value: formatDate(deal.expected_close_date) },
                ...(deal.closed_at ? [{ label: "Closed", value: formatDateTime(deal.closed_at) }] : []),
                {
                  label: "Company",
                  value: deal.company && (
                    <Link href={`/companies/${deal.company.id}`} className="text-primary hover:underline">
                      {deal.company.name}
                    </Link>
                  ),
                },
                {
                  label: "Contact",
                  value: deal.contact && (
                    <Link href={`/contacts/${deal.contact.id}`} className="text-primary hover:underline">
                      {deal.contact.name}
                    </Link>
                  ),
                },
                { label: "Owner", value: <OwnerCell owner={deal.owner} /> },
                { label: "Created", value: formatDate(deal.created_at) },
              ]}
            />
            {deal.description && (
              <div className="mt-4 border-t pt-4">
                <p className="mb-1 text-sm text-muted-foreground">Description</p>
                <p className="text-sm whitespace-pre-line">{deal.description}</p>
              </div>
            )}
          </CardContent>
        </Card>
        <div className="min-w-0 lg:col-span-2">
          <DealTabs deal={deal} />
        </div>
      </div>

      <DealFormDialog open={editing} onOpenChange={setEditing} deal={deal} />
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title="Delete deal?"
        description={`${deal.name} will be permanently deleted.`}
        isPending={remove.isPending}
        onConfirm={() => remove.mutate(deal.id, { onSuccess: () => router.replace("/deals") })}
      />
    </>
  );
}
