"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { myOrganizationsKey } from "@/features/organizations/hooks";
import { useCurrentOrganization } from "@/features/organizations/organization-gate";
import { getErrorMessage } from "@/lib/api-client";
import { organizationsService } from "@/services/organizations";

const schema = z.object({ name: z.string().trim().min(1, "Name is required").max(100) });

export function OrganizationSettings() {
  const organization = useCurrentOrganization();
  const queryClient = useQueryClient();
  const rename = useMutation({
    mutationFn: (name: string) => organizationsService.rename(name),
    onSuccess: () => {
      toast.success("Organization renamed");
      return queryClient.invalidateQueries({ queryKey: myOrganizationsKey });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm({ resolver: zodResolver(schema), values: { name: organization.name } });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization</CardTitle>
        <CardDescription>
          Everything in this workspace (contacts, companies, leads, deals, pipelines, lead sources) belongs to this
          organization and is only visible to its members.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit((values) => rename.mutate(values.name))} className="max-w-md space-y-4" noValidate>
          <FormField label="Name" htmlFor="org-name" error={errors.name?.message}>
            <Input id="org-name" {...register("name")} />
          </FormField>
          <Button type="submit" disabled={!isDirty || rename.isPending}>
            Save
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
