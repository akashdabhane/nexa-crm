"use client";

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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { formatDate } from "@/utils/format";

import { ContactFormDialog } from "./contact-form-dialog";
import { contactHooks } from "./hooks";
import { ContactTabs } from "./contact-tabs";

export function ContactDetail({ id }: { id: string }) {
  const router = useRouter();
  const { canEdit, isManager } = useCurrentUser();
  const { data: contact, isLoading, error, refetch } = contactHooks.useOne(id);
  const remove = contactHooks.useDelete();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (isLoading) return <DetailSkeleton />;
  if (error || !contact) return <ErrorState error={error} onRetry={refetch} />;

  return (
    <>
      <RecordHeader
        backHref="/contacts"
        backLabel="Contacts"
        title={contact.full_name}
        avatar={<UserAvatar name={contact.full_name} className="size-12 text-base" />}
        badges={<StatusBadge value={contact.status} />}
        subtitle={
          <>
            {contact.job_title ?? "No title"}
            {contact.company && (
              <>
                {" at "}
                <Link href={`/companies/${contact.company.id}`} className="font-medium text-foreground hover:underline">
                  {contact.company.name}
                </Link>
              </>
            )}
          </>
        }
        onEdit={canEdit(contact) ? () => setEditing(true) : undefined}
        onDelete={isManager ? () => setDeleting(true) : undefined}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <DetailList
              items={[
                { label: "Email", value: contact.email && <a href={`mailto:${contact.email}`} className="text-primary hover:underline">{contact.email}</a> },
                { label: "Phone", value: contact.phone },
                { label: "Website", value: contact.website },
                { label: "Address", value: [contact.address, contact.city, contact.country].filter(Boolean).join(", ") || null },
                { label: "Owner", value: <OwnerCell owner={contact.owner} /> },
                {
                  label: "Tags",
                  value: contact.tags.length ? (
                    <div className="flex flex-wrap gap-1">
                      {contact.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="font-normal">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  ) : null,
                },
                { label: "Created", value: formatDate(contact.created_at) },
                { label: "Updated", value: formatDate(contact.updated_at) },
              ]}
            />
          </CardContent>
        </Card>
        <div className="min-w-0 lg:col-span-2">
          <ContactTabs contact={contact} />
        </div>
      </div>

      <ContactFormDialog open={editing} onOpenChange={setEditing} contact={contact} />
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title="Delete contact?"
        description={`${contact.full_name} will be permanently deleted. Deals and activities stay but lose the link to this contact.`}
        isPending={remove.isPending}
        onConfirm={() => remove.mutate(contact.id, { onSuccess: () => router.replace("/contacts") })}
      />
    </>
  );
}
