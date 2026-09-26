"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { currentUserKey, roleLabel, useCurrentUser } from "@/hooks/use-current-user";
import { getErrorMessage } from "@/lib/api-client";
import { usersService } from "@/services/users";

const schema = z.object({ full_name: z.string().trim().min(1, "Name is required").max(255) });

export function ProfileSettings() {
  const { user } = useCurrentUser();
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: usersService.updateMe,
    onSuccess: (profile) => {
      queryClient.setQueryData(currentUserKey, profile);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Profile updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm({ resolver: zodResolver(schema), values: { full_name: user?.full_name ?? "" } });

  if (!user) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your profile</CardTitle>
        <CardDescription>Your name is shown on records you own and entries you log.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit((values) => save.mutate(values))} className="max-w-md space-y-4" noValidate>
          <FormField label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
            <Input id="full_name" {...register("full_name")} />
          </FormField>
          <FormField label="Email" htmlFor="email" hint="Managed by your login provider.">
            <Input id="email" value={user.email} disabled />
          </FormField>
          <div className="flex items-center gap-2 text-sm">
            Role: <StatusBadge value={user.role} label={roleLabel(user.role)} />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={!isDirty || save.isPending}>
              Save
            </Button>
            <Button type="button" variant="outline" asChild>
              <Link href="/reset-password">Change password</Link>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
