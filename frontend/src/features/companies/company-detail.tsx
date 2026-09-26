"use client";

import { Building2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { DetailList } from "@/components/shared/detail-list";
import { OwnerCell } from "@/components/shared/owner-cell";
import { RecordHeader } from "@/components/shared/record-header";
import { DetailSkeleton, ErrorState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { formatCurrency, formatDate, formatNumber } from "@/utils/format";

import { CompanyFormDialog } from "./company-form-dialog";
import { CompanyTabs } from "./company-tabs";
import { companyHooks } from "./hooks";

function websiteUrl(website: string) {
  return website.startsWith("http") ? website : `https://${website}`;
}

export function CompanyDetail({ id }: { id: string }) {
  const router = useRouter();
  const { canEdit, isManager } = useCurrentUser();
  const { data: company, isLoading, error, refetch } = companyHooks.useOne(id);
  const remove = companyHooks.useDelete();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (isLoading) return <DetailSkeleton />;
  if (error || !company) return <ErrorState error={error} onRetry={refetch} />;

  const stats = [
    { label: "Contacts", value: company.contact_count },
    { label: "Deals", value: company.deal_count },
    { label: "Open pipeline", value: formatCurrency(company.open_deal_value, "USD", true) },
  ];

  return (
    <>
      <RecordHeader
        backHref="/companies"
        backLabel="Companies"
        title={company.name}
        avatar={
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Building2 className="size-6" />
          </div>
        }
        badges={company.industry && <Badge variant="secondary">{company.industry}</Badge>}
        subtitle={[company.city, company.country].filter(Boolean).join(", ") || undefined}
        onEdit={canEdit(company) ? () => setEditing(true) : undefined}
        onDelete={isManager ? () => setDeleting(true) : undefined}
      />

      <div className="grid gap-3 sm:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label} className="py-4">
            <CardContent className="px-4">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <p className="text-xl font-semibold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <DetailList
              items={[
                {
                  label: "Website",
                  value: company.website && (
                    <a href={websiteUrl(company.website)} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      {company.website}
                    </a>
                  ),
                },
                { label: "Email", value: company.email },
                { label: "Phone", value: company.phone },
                { label: "Employees", value: formatNumber(company.employee_count) },
                { label: "Address", value: [company.address, company.city, company.country].filter(Boolean).join(", ") || null },
                { label: "Owner", value: <OwnerCell owner={company.owner} /> },
                { label: "Created", value: formatDate(company.created_at) },
              ]}
            />
          </CardContent>
        </Card>
        <div className="min-w-0 lg:col-span-2">
          <CompanyTabs company={company} />
        </div>
      </div>

      <CompanyFormDialog open={editing} onOpenChange={setEditing} company={company} />
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title="Delete company?"
        description={`${company.name} will be permanently deleted. Its contacts and deals are kept but unlinked.`}
        isPending={remove.isPending}
        onConfirm={() => remove.mutate(company.id, { onSuccess: () => router.replace("/companies") })}
      />
    </>
  );
}
