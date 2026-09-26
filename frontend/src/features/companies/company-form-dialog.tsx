"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCurrentUser } from "@/hooks/use-current-user";
import type { Company, CompanyInput } from "@/types";

import { companyHooks } from "./hooks";

const schema = z.object({
  name: z.string().trim().min(1, "Company name is required").max(255),
  industry: z.string().max(100),
  website: z.string().max(255),
  email: z.union([z.literal(""), z.email("Enter a valid email")]),
  phone: z.string().max(50),
  address: z.string(),
  city: z.string().max(100),
  country: z.string().max(100),
  employee_count: z.string().regex(/^\d*$/, "Enter a whole number"),
  owner_id: z.string().nullable(),
});
type Values = z.infer<typeof schema>;

function toValues(company?: Company): Values {
  return {
    name: company?.name ?? "",
    industry: company?.industry ?? "",
    website: company?.website ?? "",
    email: company?.email ?? "",
    phone: company?.phone ?? "",
    address: company?.address ?? "",
    city: company?.city ?? "",
    country: company?.country ?? "",
    employee_count: company?.employee_count?.toString() ?? "",
    owner_id: company?.owner?.id ?? null,
  };
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  company?: Company;
  onSaved?: (company: Company) => void;
};

export function CompanyFormDialog({ open, onOpenChange, company, onSaved }: Props) {
  const { isManager } = useCurrentUser();
  const create = companyHooks.useCreate();
  const update = companyHooks.useUpdate();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(company) });

  async function onSubmit(values: Values) {
    const { owner_id, employee_count, ...rest } = values;
    const data: CompanyInput = {
      ...rest,
      employee_count: employee_count ? Number(employee_count) : null,
      ...(isManager ? { owner_id } : {}),
    };
    try {
      const saved = company ? await update.mutateAsync({ id: company.id, data }) : await create.mutateAsync(data);
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
          <DialogTitle>{company ? "Edit company" : "New company"}</DialogTitle>
          <DialogDescription>Accounts group contacts and deals from the same organization.</DialogDescription>
        </DialogHeader>
        <form id="company-form" onSubmit={handleSubmit(onSubmit)} className="grid max-h-[65vh] gap-4 overflow-y-auto px-1 sm:grid-cols-2" noValidate>
          <FormField label="Company name" htmlFor="name" required error={errors.name?.message} className="sm:col-span-2">
            <Input id="name" {...register("name")} />
          </FormField>
          <FormField label="Industry" htmlFor="industry" error={errors.industry?.message}>
            <Input id="industry" placeholder="e.g. Software" {...register("industry")} />
          </FormField>
          <FormField label="Employees" htmlFor="employee_count" error={errors.employee_count?.message}>
            <Input id="employee_count" inputMode="numeric" {...register("employee_count")} />
          </FormField>
          <FormField label="Website" htmlFor="website" error={errors.website?.message}>
            <Input id="website" placeholder="example.com" {...register("website")} />
          </FormField>
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" {...register("email")} />
          </FormField>
          <FormField label="Phone" htmlFor="phone" error={errors.phone?.message}>
            <Input id="phone" {...register("phone")} />
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
          <FormField label="Address" htmlFor="address" className="sm:col-span-2">
            <Textarea id="address" rows={2} {...register("address")} />
          </FormField>
          <FormField label="City" htmlFor="city">
            <Input id="city" {...register("city")} />
          </FormField>
          <FormField label="Country" htmlFor="country">
            <Input id="country" {...register("country")} />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="company-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : company ? "Save changes" : "Create company"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
