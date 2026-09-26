"use client";

import { Plus, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { EntityRef } from "@/types";

import { ContactFormDialog } from "./contact-form-dialog";
import { contactHooks } from "./hooks";

/** Compact list of a company's contacts with an "Add contact" shortcut. */
export function RelatedContacts({ company }: { company: EntityRef }) {
  const [adding, setAdding] = useState(false);
  const { data, isLoading } = contactHooks.useList({ company_id: company.id, page_size: 50, sort_by: "first_name", sort_order: "asc" });

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
          <Plus /> Add contact
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data?.items.length ? (
        <ul className="divide-y rounded-lg border">
          {data.items.map((contact) => (
            <li key={contact.id} className="flex items-center gap-3 p-3">
              <UserAvatar name={contact.full_name} className="size-8" />
              <div className="min-w-0 flex-1">
                <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline">
                  {contact.full_name}
                </Link>
                <p className="truncate text-xs text-muted-foreground">
                  {[contact.job_title, contact.email].filter(Boolean).join(" · ") || "—"}
                </p>
              </div>
              <StatusBadge value={contact.status} />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState icon={Users} title="No contacts yet" description={`Add the people you work with at ${company.name}.`} />
      )}
      <ContactFormDialog open={adding} onOpenChange={setAdding} defaultCompany={company} />
    </div>
  );
}
