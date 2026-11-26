"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UserMinus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { StatusBadge } from "@/components/shared/status-badge";
import { UserAvatar } from "@/components/shared/user-avatar";
import { useUsers } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { roleLabel, useCurrentUser } from "@/hooks/use-current-user";
import { getErrorMessage } from "@/lib/api-client";
import { usersService } from "@/services/users";
import type { Member, UserRole } from "@/types";
import { formatDate } from "@/utils/format";

import { InvitationsSettings } from "./invitations-settings";

const ROLES: UserRole[] = ["admin", "manager", "sales_rep"];

export function UsersSettings() {
  const { user: me } = useCurrentUser();
  const { data: users, isLoading } = useUsers();
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: UserRole; is_active?: boolean } }) =>
      usersService.update(id, data),
    onSuccess: () => {
      toast.success("User updated");
      return queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const [removing, setRemoving] = useState<Member | null>(null);
  const remove = useMutation({
    mutationFn: (id: string) => usersService.remove(id),
    onSuccess: () => {
      toast.success("Removed from the organization");
      setRemoving(null);
      return queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  return (
    <div className="space-y-6">
      <InvitationsSettings />
      <Card>
        <CardHeader>
          <CardTitle>Members & roles</CardTitle>
          <CardDescription>
            Roles apply in this organization only. Admins manage everything, Managers can edit, reassign and delete any
            record, Sales Reps edit only their own records. Turning &quot;Active&quot; off blocks someone&apos;s access
            to this organization without removing them; removing them keeps the records they own.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {isLoading ? (
            <Skeleton className="h-40" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {users?.map((user) => {
                  const isMe = user.id === me?.id;
                  return (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <UserAvatar name={user.full_name} className="size-8" />
                          <div>
                            <p className="font-medium">
                              {user.full_name}{" "}
                              {isMe && <span className="text-xs font-normal text-muted-foreground">(you)</span>}
                            </p>
                            <p className="text-xs text-muted-foreground">{user.email}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {isMe ? (
                          <StatusBadge value={user.role} label={roleLabel(user.role)} />
                        ) : (
                          <Select
                            value={user.role}
                            onValueChange={(role) => update.mutate({ id: user.id, data: { role: role as UserRole } })}
                          >
                            <SelectTrigger className="w-36" aria-label={`Role for ${user.full_name}`}>
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
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={user.is_active}
                          disabled={isMe}
                          onCheckedChange={(checked) => update.mutate({ id: user.id, data: { is_active: checked } })}
                          aria-label={`${user.full_name} active`}
                        />
                      </TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(user.created_at)}</TableCell>
                      <TableCell>
                        {!isMe && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setRemoving(user)}
                            aria-label={`Remove ${user.full_name} from the organization`}
                          >
                            <UserMinus />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title={`Remove ${removing?.full_name ?? "member"}?`}
        description="They lose access to this organization right away. Records they own stay and remain assigned to them. You can invite them again later."
        confirmLabel="Remove"
        isPending={remove.isPending}
        onConfirm={() => removing && remove.mutate(removing.id)}
      />
    </div>
  );
}
