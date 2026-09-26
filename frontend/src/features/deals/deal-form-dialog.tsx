"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { EntityCombobox } from "@/components/shared/entity-combobox";
import { FormField } from "@/components/shared/form-field";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useCurrentUser } from "@/hooks/use-current-user";
import { companiesService } from "@/services/companies";
import { contactsService } from "@/services/contacts";
import { CURRENCIES, type Deal, type DealInput, type EntityRef } from "@/types";

import { dealHooks, useDefaultPipeline } from "./hooks";

const schema = z.object({
  name: z.string().trim().min(1, "Deal name is required").max(255),
  value: z.number({ error: "Enter an amount" }).min(0, "Must be positive"),
  currency: z.string().length(3),
  stage_id: z.string().nullable(),
  expected_close_date: z.string(),
  company_id: z.string().nullable(),
  contact_id: z.string().nullable(),
  owner_id: z.string().nullable(),
  description: z.string(),
});
type Values = z.infer<typeof schema>;

type Defaults = { company?: EntityRef | null; contact?: EntityRef | null; stageId?: string };

function toValues(deal?: Deal, defaults: Defaults = {}): Values {
  return {
    name: deal?.name ?? "",
    value: deal?.value ?? 0,
    currency: deal?.currency ?? "USD",
    stage_id: deal?.stage.id ?? defaults.stageId ?? null,
    expected_close_date: deal?.expected_close_date ?? "",
    company_id: deal?.company?.id ?? defaults.company?.id ?? null,
    contact_id: deal?.contact?.id ?? defaults.contact?.id ?? null,
    owner_id: deal?.owner?.id ?? null,
    description: deal?.description ?? "",
  };
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deal?: Deal;
  defaults?: Defaults;
  onSaved?: (deal: Deal) => void;
};

export function DealFormDialog({ open, onOpenChange, deal, defaults, onSaved }: Props) {
  const { isManager } = useCurrentUser();
  const { pipeline } = useDefaultPipeline();
  const create = dealHooks.useCreate();
  const update = dealHooks.useUpdate();
  const {
    register,
    control,
    setValue,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(deal, defaults) });
  const companyId = useWatch({ control, name: "company_id" });

  async function onSubmit(values: Values) {
    const { owner_id, stage_id, expected_close_date, ...rest } = values;
    const data: DealInput = {
      ...rest,
      expected_close_date: expected_close_date || null,
      ...(stage_id ? { stage_id } : {}),
      ...(isManager ? { owner_id } : {}),
    };
    try {
      const saved = deal ? await update.mutateAsync({ id: deal.id, data }) : await create.mutateAsync(data);
      onSaved?.(saved);
      onOpenChange(false);
    } catch {
      // Error toast already shown.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{deal ? "Edit deal" : "New deal"}</DialogTitle>
          <DialogDescription>An opportunity you&apos;re working to close.</DialogDescription>
        </DialogHeader>
        <form id="deal-form" onSubmit={handleSubmit(onSubmit)} className="grid max-h-[65vh] gap-4 overflow-y-auto px-1 sm:grid-cols-2" noValidate>
          <FormField label="Deal name" htmlFor="name" required error={errors.name?.message} className="sm:col-span-2">
            <Input id="name" placeholder="e.g. Annual license — Acme" {...register("name")} />
          </FormField>
          <div className="grid grid-cols-3 gap-2">
            <FormField label="Value" htmlFor="value" error={errors.value?.message} className="col-span-2">
              <Input id="value" type="number" min={0} step="0.01" {...register("value", { valueAsNumber: true })} />
            </FormField>
            <FormField label="Currency" htmlFor="currency">
              <Controller
                control={control}
                name="currency"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="currency" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((currency) => (
                        <SelectItem key={currency} value={currency}>
                          {currency}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>
          </div>
          <FormField label="Stage" htmlFor="stage_id">
            <Controller
              control={control}
              name="stage_id"
              render={({ field }) => (
                <Select value={field.value ?? undefined} onValueChange={field.onChange}>
                  <SelectTrigger id="stage_id" className="w-full">
                    <SelectValue placeholder="First stage" />
                  </SelectTrigger>
                  <SelectContent>
                    {pipeline?.stages.map((stage) => (
                      <SelectItem key={stage.id} value={stage.id}>
                        {stage.name} · {stage.probability}%
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <FormField label="Company" htmlFor="company_id">
            <Controller
              control={control}
              name="company_id"
              render={({ field }) => (
                <EntityCombobox
                  id="company_id"
                  queryKey="companies"
                  fetchOptions={(search) => companiesService.options({ search })}
                  value={field.value}
                  selectedLabel={deal?.company?.name ?? defaults?.company?.name}
                  onChange={(value) => {
                    field.onChange(value);
                    if (value !== companyId) setValue("contact_id", null);
                  }}
                  placeholder="Select company"
                />
              )}
            />
          </FormField>
          <FormField label="Primary contact" htmlFor="contact_id">
            <Controller
              control={control}
              name="contact_id"
              render={({ field }) => (
                <EntityCombobox
                  id="contact_id"
                  queryKey={`contacts-${companyId ?? "all"}`}
                  fetchOptions={(search) => contactsService.options({ search, company_id: companyId ?? undefined })}
                  value={field.value}
                  selectedLabel={deal?.contact?.name ?? defaults?.contact?.name}
                  onChange={field.onChange}
                  placeholder="Select contact"
                />
              )}
            />
          </FormField>
          <FormField label="Expected close date" htmlFor="expected_close_date">
            <Input id="expected_close_date" type="date" {...register("expected_close_date")} />
          </FormField>
          {isManager && (
            <FormField label="Assigned to" htmlFor="owner_id">
              <Controller
                control={control}
                name="owner_id"
                render={({ field }) => <UserSelect id="owner_id" value={field.value} onChange={field.onChange} allowEmpty />}
              />
            </FormField>
          )}
          <FormField label="Description" htmlFor="description" className="sm:col-span-2">
            <Textarea id="description" rows={3} {...register("description")} />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="deal-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : deal ? "Save changes" : "Create deal"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
