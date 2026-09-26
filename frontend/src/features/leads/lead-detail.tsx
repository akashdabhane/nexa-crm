"use client";

import { CheckCircle2, Repeat } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { DetailList } from "@/components/shared/detail-list";
import { OwnerCell } from "@/components/shared/owner-cell";
import { RecordHeader } from "@/components/shared/record-header";
import { DetailSkeleton, ErrorState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { formatDate, formatDateTime, humanize } from "@/utils/format";

import { ConvertLeadDialog } from "./convert-lead-dialog";
import { leadHooks } from "./hooks";
import { LeadFormDialog } from "./lead-form-dialog";
import { LeadTabs } from "./lead-tabs";
import { ScoreBar } from "./score-bar";

export function LeadDetail({ id }: { id: string }) {
  const router = useRouter();
  const { canEdit, isManager } = useCurrentUser();
  const { data: lead, isLoading, error, refetch } = leadHooks.useOne(id);
  const remove = leadHooks.useDelete();
  const [editing, setEditing] = useState(false);
  const [converting, setConverting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (isLoading) return <DetailSkeleton />;
  if (error || !lead) return <ErrorState error={error} onRetry={refetch} />;

  const isConverted = lead.status === "converted";
  const editable = canEdit(lead);

  return (
    <>
      <RecordHeader
        backHref="/leads"
        backLabel="Leads"
        title={lead.name}
        avatar={<UserAvatar name={lead.name} className="size-12 text-base" />}
        badges={<StatusBadge value={lead.status} />}
        subtitle={lead.company_name ?? "No company"}
        actions={
          !isConverted &&
          editable && (
            <Button onClick={() => setConverting(true)}>
              <Repeat /> Convert
            </Button>
          )
        }
        onEdit={editable ? () => setEditing(true) : undefined}
        onDelete={isManager ? () => setDeleting(true) : undefined}
      />

      {isConverted && (
        <div className="flex flex-col gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2">
            <CheckCircle2 className="size-4" /> Converted on {formatDateTime(lead.converted_at)}
          </p>
          <div className="flex flex-wrap gap-3 font-medium">
            {lead.converted_contact_id && <Link href={`/contacts/${lead.converted_contact_id}`} className="underline">View contact</Link>}
            {lead.converted_company_id && <Link href={`/companies/${lead.converted_company_id}`} className="underline">View company</Link>}
            {lead.converted_deal_id && <Link href={`/deals/${lead.converted_deal_id}`} className="underline">View deal</Link>}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <DetailList
              items={[
                { label: "Email", value: lead.email },
                { label: "Phone", value: lead.phone },
                { label: "Company", value: lead.company_name },
                { label: "Source", value: humanize(lead.source) },
                { label: "Score", value: <ScoreBar score={lead.score} /> },
                { label: "Owner", value: <OwnerCell owner={lead.owner} /> },
                { label: "Created", value: formatDate(lead.created_at) },
              ]}
            />
          </CardContent>
        </Card>
        <div className="min-w-0 lg:col-span-2">
          <LeadTabs lead={lead} />
        </div>
      </div>

      <LeadFormDialog open={editing} onOpenChange={setEditing} lead={lead} />
      {!isConverted && <ConvertLeadDialog lead={lead} open={converting} onOpenChange={setConverting} />}
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title="Delete lead?"
        description={`${lead.name} will be permanently deleted.`}
        isPending={remove.isPending}
        onConfirm={() => remove.mutate(lead.id, { onSuccess: () => router.replace("/leads") })}
      />
    </>
  );
}
