"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { EntityCombobox } from "@/components/shared/entity-combobox";
import { FormField } from "@/components/shared/form-field";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { companiesService } from "@/services/companies";
import { contactsService } from "@/services/contacts";
import { dealsService } from "@/services/deals";
import { ACTIVITY_TYPES, type RecordLinks } from "@/types";

import { ACTIVITY_ICONS } from "./activity-icons";
import { activityHooks } from "./hooks";

const schema = z
  .object({
    type: z.enum(ACTIVITY_TYPES),
    subject: z.string().trim().min(1, "Subject is required").max(255),
    description: z.string(),
    occurred_at: z.string().min(1, "Pick a date and time"),
    duration_minutes: z.string().regex(/^\d*$/, "Minutes as a whole number"),
    contact_id: z.string().nullable(),
    company_id: z.string().nullable(),
    deal_id: z.string().nullable(),
    lead_id: z.string().nullable(),
  })
  .refine((v) => v.contact_id || v.company_id || v.deal_id || v.lead_id, {
    message: "Link the activity to a contact, company or deal",
    path: ["contact_id"],
  });
type Values = z.infer<typeof schema>;

/** Current local time formatted for <input type="datetime-local">. */
function nowLocal() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** When set, the activity is attached to these records and the pickers are hidden. */
  links?: RecordLinks;
};

export function LogActivityDialog({ open, onOpenChange, links }: Props) {
  const create = activityHooks.useCreate();
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    values: {
      type: "call",
      subject: "",
      description: "",
      occurred_at: nowLocal(),
      duration_minutes: "",
      contact_id: links?.contact_id ?? null,
      company_id: links?.company_id ?? null,
      deal_id: links?.deal_id ?? null,
      lead_id: links?.lead_id ?? null,
    },
  });

  async function onSubmit({ duration_minutes, occurred_at, ...values }: Values) {
    try {
      await create.mutateAsync({
        ...values,
        occurred_at: new Date(occurred_at).toISOString(),
        duration_minutes: duration_minutes ? Number(duration_minutes) : null,
      });
      reset();
      onOpenChange(false);
    } catch {
      // Error toast already shown.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Log activity</DialogTitle>
          <DialogDescription>Record a call, meeting or email.</DialogDescription>
        </DialogHeader>
        <form id="activity-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <Controller
            control={control}
            name="type"
            render={({ field }) => (
              <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Activity type">
                {ACTIVITY_TYPES.map((type) => {
                  const { icon: Icon, label } = ACTIVITY_ICONS[type];
                  return (
                    <button
                      key={type}
                      type="button"
                      role="radio"
                      aria-checked={field.value === type}
                      onClick={() => field.onChange(type)}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-lg border p-2 text-sm transition-colors",
                        field.value === type ? "border-primary bg-primary/5 font-medium text-primary" : "hover:bg-muted",
                      )}
                    >
                      <Icon className="size-4" /> {label}
                    </button>
                  );
                })}
              </div>
            )}
          />
          <FormField label="Subject" htmlFor="subject" required error={errors.subject?.message}>
            <Input id="subject" placeholder="e.g. Discovery call" {...register("subject")} />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="When" htmlFor="occurred_at" error={errors.occurred_at?.message}>
              <Input id="occurred_at" type="datetime-local" {...register("occurred_at")} />
            </FormField>
            <FormField label="Duration (min)" htmlFor="duration_minutes" error={errors.duration_minutes?.message}>
              <Input id="duration_minutes" inputMode="numeric" {...register("duration_minutes")} />
            </FormField>
          </div>
          {!links && (
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Contact" htmlFor="contact_id" error={errors.contact_id?.message}>
                <Controller
                  control={control}
                  name="contact_id"
                  render={({ field }) => (
                    <EntityCombobox
                      id="contact_id"
                      queryKey="contacts"
                      fetchOptions={(search) => contactsService.options({ search })}
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="Select contact"
                    />
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
                      onChange={field.onChange}
                      placeholder="Select company"
                    />
                  )}
                />
              </FormField>
              <FormField label="Deal" htmlFor="deal_id" className="sm:col-span-2">
                <Controller
                  control={control}
                  name="deal_id"
                  render={({ field }) => (
                    <EntityCombobox
                      id="deal_id"
                      queryKey="deals"
                      fetchOptions={(search) =>
                        dealsService.list({ search, page_size: 20, status: "open" }).then((page) => page.items.map((d) => ({ id: d.id, name: d.name })))
                      }
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="Select deal"
                    />
                  )}
                />
              </FormField>
            </div>
          )}
          <FormField label="Notes" htmlFor="description">
            <Textarea id="description" rows={3} placeholder="What was discussed? Next steps?" {...register("description")} />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="activity-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Log activity"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
