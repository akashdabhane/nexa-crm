"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
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
import { CONTACT_STATUSES, type Contact, type ContactInput, type EntityRef } from "@/types";
import { humanize } from "@/utils/format";

import { contactHooks } from "./hooks";

const schema = z.object({
  first_name: z.string().trim().min(1, "First name is required").max(100),
  last_name: z.string().max(100),
  email: z.union([z.literal(""), z.email("Enter a valid email")]),
  phone: z.string().max(50),
  job_title: z.string().max(150),
  website: z.string().max(255),
  address: z.string(),
  city: z.string().max(100),
  country: z.string().max(100),
  status: z.enum(CONTACT_STATUSES),
  tags: z.string(),
  company_id: z.string().nullable(),
  owner_id: z.string().nullable(),
});
type Values = z.infer<typeof schema>;

function toValues(contact?: Contact, defaultCompany?: EntityRef | null): Values {
  return {
    first_name: contact?.first_name ?? "",
    last_name: contact?.last_name ?? "",
    email: contact?.email ?? "",
    phone: contact?.phone ?? "",
    job_title: contact?.job_title ?? "",
    website: contact?.website ?? "",
    address: contact?.address ?? "",
    city: contact?.city ?? "",
    country: contact?.country ?? "",
    status: contact?.status ?? "active",
    tags: contact?.tags.join(", ") ?? "",
    company_id: contact?.company?.id ?? defaultCompany?.id ?? null,
    owner_id: contact?.owner?.id ?? null,
  };
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contact?: Contact;
  /** Pre-selects the company when adding a contact from a company page. */
  defaultCompany?: EntityRef | null;
  onSaved?: (contact: Contact) => void;
};

export function ContactFormDialog({ open, onOpenChange, contact, defaultCompany, onSaved }: Props) {
  const { isManager } = useCurrentUser();
  const create = contactHooks.useCreate();
  const update = contactHooks.useUpdate();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(contact, defaultCompany) });

  async function onSubmit(values: Values) {
    const { owner_id, tags, ...rest } = values;
    const data: ContactInput = {
      ...rest,
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      ...(isManager ? { owner_id } : {}),
    };
    try {
      const saved = contact ? await update.mutateAsync({ id: contact.id, data }) : await create.mutateAsync(data);
      onSaved?.(saved);
      onOpenChange(false);
    } catch {
      // The mutation already shows an error toast; keep the dialog open.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{contact ? "Edit contact" : "New contact"}</DialogTitle>
          <DialogDescription>People you talk to at your customers and prospects.</DialogDescription>
        </DialogHeader>
        <form id="contact-form" onSubmit={handleSubmit(onSubmit)} className="grid max-h-[65vh] gap-4 overflow-y-auto px-1 sm:grid-cols-2" noValidate>
          <FormField label="First name" htmlFor="first_name" required error={errors.first_name?.message}>
            <Input id="first_name" {...register("first_name")} />
          </FormField>
          <FormField label="Last name" htmlFor="last_name" error={errors.last_name?.message}>
            <Input id="last_name" {...register("last_name")} />
          </FormField>
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" {...register("email")} />
          </FormField>
          <FormField label="Phone" htmlFor="phone" error={errors.phone?.message}>
            <Input id="phone" {...register("phone")} />
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
                  selectedLabel={contact?.company?.name ?? defaultCompany?.name}
                  onChange={field.onChange}
                  placeholder="Select company"
                />
              )}
            />
          </FormField>
          <FormField label="Job title" htmlFor="job_title" error={errors.job_title?.message}>
            <Input id="job_title" {...register("job_title")} />
          </FormField>
          <FormField label="Status" htmlFor="status">
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="status" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CONTACT_STATUSES.map((status) => (
                      <SelectItem key={status} value={status}>
                        {humanize(status)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          {isManager ? (
            <FormField label="Assigned to" htmlFor="owner_id">
              <Controller
                control={control}
                name="owner_id"
                render={({ field }) => <UserSelect id="owner_id" value={field.value} onChange={field.onChange} allowEmpty />}
              />
            </FormField>
          ) : (
            <div />
          )}
          <FormField label="Tags" htmlFor="tags" hint="Separate tags with commas" className="sm:col-span-2">
            <Input id="tags" placeholder="vip, decision-maker" {...register("tags")} />
          </FormField>
          <FormField label="Website" htmlFor="website">
            <Input id="website" {...register("website")} />
          </FormField>
          <FormField label="City" htmlFor="city">
            <Input id="city" {...register("city")} />
          </FormField>
          <FormField label="Address" htmlFor="address">
            <Textarea id="address" rows={2} {...register("address")} />
          </FormField>
          <FormField label="Country" htmlFor="country">
            <Input id="country" {...register("country")} />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="contact-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : contact ? "Save changes" : "Create contact"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
