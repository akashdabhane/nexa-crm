"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCurrentUser } from "@/hooks/use-current-user";
import { LEAD_SOURCES, LEAD_STATUSES, type Lead, type LeadInput } from "@/types";
import { humanize } from "@/utils/format";

import { leadHooks } from "./hooks";

const EDITABLE_STATUSES = LEAD_STATUSES.filter((status) => status !== "converted");

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200),
  email: z.union([z.literal(""), z.email("Enter a valid email")]),
  phone: z.string().max(50),
  company_name: z.string().max(255),
  source: z.enum(LEAD_SOURCES),
  status: z.enum(LEAD_STATUSES),
  score: z.number({ error: "Enter a score" }).int().min(0, "0–100").max(100, "0–100"),
  owner_id: z.string().nullable(),
});
type Values = z.infer<typeof schema>;

function toValues(lead?: Lead): Values {
  return {
    name: lead?.name ?? "",
    email: lead?.email ?? "",
    phone: lead?.phone ?? "",
    company_name: lead?.company_name ?? "",
    source: lead?.source ?? "website",
    status: lead?.status ?? "new",
    score: lead?.score ?? 0,
    owner_id: lead?.owner?.id ?? null,
  };
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead?: Lead;
  onSaved?: (lead: Lead) => void;
};

export function LeadFormDialog({ open, onOpenChange, lead, onSaved }: Props) {
  const { isManager } = useCurrentUser();
  const create = leadHooks.useCreate();
  const update = leadHooks.useUpdate();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(lead) });
  const isConverted = lead?.status === "converted";

  async function onSubmit(values: Values) {
    const { owner_id, status, ...rest } = values;
    const data: LeadInput = { ...rest, ...(isConverted ? {} : { status }), ...(isManager ? { owner_id } : {}) };
    try {
      const saved = lead ? await update.mutateAsync({ id: lead.id, data }) : await create.mutateAsync(data);
      onSaved?.(saved);
      onOpenChange(false);
    } catch {
      // The mutation already shows an error toast; keep the dialog open.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{lead ? "Edit lead" : "New lead"}</DialogTitle>
          <DialogDescription>A potential customer you haven&apos;t qualified yet.</DialogDescription>
        </DialogHeader>
        <form id="lead-form" onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
          <FormField label="Name" htmlFor="name" required error={errors.name?.message}>
            <Input id="name" {...register("name")} />
          </FormField>
          <FormField label="Company" htmlFor="company_name" error={errors.company_name?.message}>
            <Input id="company_name" {...register("company_name")} />
          </FormField>
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" {...register("email")} />
          </FormField>
          <FormField label="Phone" htmlFor="phone" error={errors.phone?.message}>
            <Input id="phone" {...register("phone")} />
          </FormField>
          <FormField label="Source" htmlFor="source">
            <Controller
              control={control}
              name="source"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="source" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LEAD_SOURCES.map((source) => (
                      <SelectItem key={source} value={source}>
                        {humanize(source)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <FormField label="Status" htmlFor="status">
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange} disabled={isConverted}>
                  <SelectTrigger id="status" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(isConverted ? LEAD_STATUSES : EDITABLE_STATUSES).map((status) => (
                      <SelectItem key={status} value={status}>
                        {humanize(status)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <FormField label="Lead score (0–100)" htmlFor="score" error={errors.score?.message}>
            <Input id="score" type="number" min={0} max={100} {...register("score", { valueAsNumber: true })} />
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
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="lead-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : lead ? "Save changes" : "Create lead"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
