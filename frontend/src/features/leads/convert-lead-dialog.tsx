"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Building2, Handshake, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { EntityCombobox } from "@/components/shared/entity-combobox";
import { FormField } from "@/components/shared/form-field";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { companiesService } from "@/services/companies";
import type { Lead } from "@/types";

import { useConvertLead } from "./hooks";

const schema = z.object({
  company_id: z.string().nullable(),
  create_deal: z.boolean(),
  deal_name: z.string().max(255),
  deal_value: z.number({ error: "Enter an amount" }).min(0, "Must be positive"),
  expected_close_date: z.string(),
});
type Values = z.infer<typeof schema>;

export function ConvertLeadDialog({ lead, open, onOpenChange }: { lead: Lead; open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const convert = useConvertLead();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_id: null,
      create_deal: true,
      deal_name: `${lead.company_name ?? lead.name} deal`,
      deal_value: 0,
      expected_close_date: "",
    },
  });
  const createDeal = useWatch({ control, name: "create_deal" });
  const companyId = useWatch({ control, name: "company_id" });

  async function onSubmit(values: Values) {
    try {
      const result = await convert.mutateAsync({
        id: lead.id,
        data: { ...values, expected_close_date: values.expected_close_date || null },
      });
      onOpenChange(false);
      router.push(result.deal_id ? `/deals/${result.deal_id}` : `/contacts/${result.contact_id}`);
    } catch {
      // Error toast already shown.
    }
  }

  const outcomes = [
    { icon: User, label: "Contact", detail: lead.name },
    {
      icon: Building2,
      label: "Company",
      detail: companyId ? "Existing company" : lead.company_name ? `${lead.company_name} (matched or new)` : "None",
    },
    { icon: Handshake, label: "Deal", detail: createDeal ? "New deal in first stage" : "Skipped" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Convert lead</DialogTitle>
          <DialogDescription>Turn {lead.name} into a contact, link a company and optionally open a deal.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-3 gap-2 rounded-lg bg-muted/50 p-3 text-xs">
          {outcomes.map(({ icon: Icon, label, detail }) => (
            <div key={label} className="space-y-1">
              <p className="flex items-center gap-1 font-medium">
                <Icon className="size-3.5" /> {label}
              </p>
              <p className="text-muted-foreground">{detail}</p>
            </div>
          ))}
        </div>

        <form id="convert-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Link to existing company (optional)" htmlFor="company_id" hint="Leave empty to match by name or create a new company.">
            <Controller
              control={control}
              name="company_id"
              render={({ field }) => (
                <EntityCombobox
                  id="company_id"
                  queryKey="companies"
                  fetchOptions={(search) => companiesService.options({ search })}
                  value={field.value}
                  onChange={field.onChange}
                  placeholder="Search companies"
                />
              )}
            />
          </FormField>

          <div className="flex items-center gap-2">
            <Controller
              control={control}
              name="create_deal"
              render={({ field }) => (
                <Checkbox id="create_deal" checked={field.value} onCheckedChange={(checked) => field.onChange(checked === true)} />
              )}
            />
            <Label htmlFor="create_deal">Create a deal</Label>
          </div>

          {createDeal && (
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Deal name" htmlFor="deal_name" className="sm:col-span-2">
                <Input id="deal_name" {...register("deal_name")} />
              </FormField>
              <FormField label="Value (USD)" htmlFor="deal_value" error={errors.deal_value?.message}>
                <Input id="deal_value" type="number" min={0} step="0.01" {...register("deal_value", { valueAsNumber: true })} />
              </FormField>
              <FormField label="Expected close" htmlFor="expected_close_date">
                <Input id="expected_close_date" type="date" {...register("expected_close_date")} />
              </FormField>
            </div>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="convert-form" disabled={isSubmitting}>
            {isSubmitting ? "Converting…" : "Convert"} <ArrowRight />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
