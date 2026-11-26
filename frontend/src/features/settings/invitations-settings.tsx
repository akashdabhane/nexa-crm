"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MailPlus, X } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCurrentOrganization } from "@/features/organizations/organization-gate";
import { roleLabel } from "@/hooks/use-current-user";
import { getErrorMessage } from "@/lib/api-client";
import { organizationsService } from "@/services/organizations";
import type { UserRole } from "@/types";
import { formatDate } from "@/utils/format";

const ROLES: UserRole[] = ["sales_rep", "manager", "admin"];
const invitationsKey = ["invitations"] as const;

const schema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  role: z.enum(["admin", "manager", "sales_rep"]),
});

/** Admins grant access to the organization by inviting an email address. */
export function InvitationsSettings() {
  const organization = useCurrentOrganization();
  const queryClient = useQueryClient();
  const { data: invitations = [] } = useQuery({ queryKey: invitationsKey, queryFn: organizationsService.invitations });

  const invite = useMutation({
    mutationFn: organizationsService.invite,
    onSuccess: (invitation) => {
      toast.success(`Invitation sent to ${invitation.email}`);
      reset({ email: "", role: invitation.role });
      return queryClient.invalidateQueries({ queryKey: invitationsKey });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const revoke = useMutation({
    mutationFn: organizationsService.revokeInvitation,
    onSuccess: () => {
      toast.success("Invitation revoked");
      return queryClient.invalidateQueries({ queryKey: invitationsKey });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { email: "", role: "sales_rep" as UserRole } });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invite people</CardTitle>
        <CardDescription>
          Signing up alone gives no access. Invite someone&apos;s email address: once they sign in with it, the
          invitation to {organization.name} appears on their Organizations page and they can accept it. Invitations
          expire after 14 days.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form
          onSubmit={handleSubmit((values) => invite.mutate(values))}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          noValidate
        >
          <FormField label="Email" htmlFor="invite-email" error={errors.email?.message} className="flex-1">
            <Input id="invite-email" type="email" placeholder="teammate@company.com" {...register("email")} />
          </FormField>
          <FormField label="Role" htmlFor="invite-role">
            <Controller
              control={control}
              name="role"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="invite-role" className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {roleLabel(role)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <Button type="submit" disabled={invite.isPending}>
            <MailPlus /> Invite
          </Button>
        </form>

        {invitations.length > 0 && (
          <div className="overflow-x-auto">
            <p className="mb-2 text-sm font-medium">Pending invitations</p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Invited by</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {invitations.map((invitation) => (
                  <TableRow key={invitation.id}>
                    <TableCell className="font-medium">{invitation.email}</TableCell>
                    <TableCell>
                      <StatusBadge value={invitation.role} label={roleLabel(invitation.role)} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">{invitation.invited_by?.full_name ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(invitation.expires_at)}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => revoke.mutate(invitation.id)}
                        disabled={revoke.isPending}
                        aria-label={`Revoke invitation for ${invitation.email}`}
                      >
                        <X />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
