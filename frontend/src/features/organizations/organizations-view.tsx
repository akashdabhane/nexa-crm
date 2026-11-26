"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, ChevronRight, LogOut, Mail, Plus, Users } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Logo } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { FormField } from "@/components/shared/form-field";
import { ErrorState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { roleLabel } from "@/hooks/use-current-user";
import { clearActiveOrganization, enterOrganization } from "@/lib/active-organization";
import { getErrorMessage } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { organizationsService } from "@/services/organizations";
import type { MyInvitation, MyOrganization } from "@/types";

import {
  myInvitationsKey,
  myOrganizationsKey,
  useActiveOrganizationId,
  useMyInvitations,
  useMyOrganizations,
} from "./hooks";

const createSchema = z.object({ name: z.string().trim().min(1, "Give your organization a name").max(100) });

async function signOut() {
  clearActiveOrganization();
  await createClient().auth.signOut();
  // A full page load so all cached data is dropped (same as the API client's sign-out).
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/login");
}

/** Home after login: pick one of your organizations, accept an invitation, or start a new organization. */
export function OrganizationsView() {
  const me = useQuery({ queryKey: ["me", "account"], queryFn: organizationsService.me });
  const organizations = useMyOrganizations();
  const invitations = useMyInvitations();
  const [creating, setCreating] = useState(false);

  const hasNothing = organizations.data?.length === 0 && invitations.data?.length === 0;

  return (
    <div className="min-h-svh bg-muted/30">
      <header className="flex h-14 items-center justify-between border-b bg-background px-4 md:px-6">
        <Logo href="/organizations" />
        <div className="flex items-center gap-2">
          {me.data && <span className="hidden text-sm text-muted-foreground sm:inline">{me.data.email}</span>}
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={signOut}>
            <LogOut /> Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl space-y-8 p-4 md:p-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your organizations</h1>
          <p className="text-sm text-muted-foreground">
            Each organization has its own contacts, leads, companies and deals. You only see the ones you belong to.
          </p>
        </div>

        {invitations.data && invitations.data.length > 0 && (
          <section className="space-y-3" aria-labelledby="invitations-heading">
            <h2 id="invitations-heading" className="text-sm font-medium text-muted-foreground">
              Invitations
            </h2>
            {invitations.data.map((invitation) => (
              <InvitationCard key={invitation.id} invitation={invitation} />
            ))}
          </section>
        )}

        <section className="space-y-3" aria-labelledby="orgs-heading">
          <h2 id="orgs-heading" className="sr-only">
            Organizations
          </h2>
          {organizations.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
            </div>
          ) : organizations.isError ? (
            <ErrorState error={organizations.error} onRetry={() => organizations.refetch()} />
          ) : (
            organizations.data?.map((org) => <OrganizationCard key={org.id} organization={org} />)
          )}

          {hasNothing && !creating && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
                <div className="flex size-10 items-center justify-center rounded-full bg-muted">
                  <Mail className="size-5 text-muted-foreground" />
                </div>
                <p className="font-medium">You&apos;re not in any organization yet</p>
                <p className="max-w-md text-sm text-muted-foreground">
                  To join your team&apos;s organization, ask one of its admins to invite{" "}
                  <span className="font-medium text-foreground">{me.data?.email ?? "your email"}</span>. The invitation
                  will appear here. Or create a new organization of your own.
                </p>
              </CardContent>
            </Card>
          )}
        </section>

        {creating ? (
          <CreateOrganizationCard onCancel={() => setCreating(false)} />
        ) : (
          <Button variant="outline" onClick={() => setCreating(true)} disabled={organizations.isLoading}>
            <Plus /> Create organization
          </Button>
        )}
      </main>
    </div>
  );
}

function OrganizationCard({ organization }: { organization: MyOrganization }) {
  const disabled = organization.status !== "active";
  const isCurrent = organization.id === useActiveOrganizationId();

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => enterOrganization(organization.id)}
      className="group flex w-full items-center gap-4 rounded-xl border bg-card p-4 text-left shadow-xs transition-colors hover:border-primary/50 hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:border-border disabled:hover:bg-card"
    >
      <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Building2 className="size-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 truncate font-medium">
          {organization.name}
          {isCurrent && <span className="text-xs font-normal text-muted-foreground">(last used)</span>}
        </p>
        <p className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="size-3.5" /> {organization.member_count}{" "}
            {organization.member_count === 1 ? "member" : "members"}
          </span>
          {disabled && <span className="text-destructive">Your access has been disabled</span>}
        </p>
      </div>
      <StatusBadge value={organization.role} label={roleLabel(organization.role)} />
      {!disabled && (
        <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
      )}
    </button>
  );
}

function InvitationCard({ invitation }: { invitation: MyInvitation }) {
  const queryClient = useQueryClient();
  const accept = useMutation({
    mutationFn: () => organizationsService.accept(invitation.id),
    onSuccess: (org) => {
      toast.success(`You joined ${org.name}`);
      enterOrganization(org.id);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const decline = useMutation({
    mutationFn: () => organizationsService.decline(invitation.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: myInvitationsKey }),
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const busy = accept.isPending || decline.isPending;

  return (
    <Card className="border-primary/40 bg-primary/5">
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <p className="font-medium">{invitation.organization.name}</p>
          <p className="text-sm text-muted-foreground">
            {invitation.invited_by ? `${invitation.invited_by.full_name} invited you` : "You're invited"} to join as{" "}
            {roleLabel(invitation.role)}.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => decline.mutate()} disabled={busy}>
            Decline
          </Button>
          <Button onClick={() => accept.mutate()} disabled={busy}>
            Accept &amp; open
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CreateOrganizationCard({ onCancel }: { onCancel: () => void }) {
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: (name: string) => organizationsService.create(name),
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: myOrganizationsKey });
      toast.success(`${org.name} created`);
      enterOrganization(org.id);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(createSchema), defaultValues: { name: "" } });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create an organization</CardTitle>
        <CardDescription>
          It starts empty, with you as its admin. You can invite your team from Settings → Users &amp; roles.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit((values) => create.mutate(values.name))} className="space-y-4" noValidate>
          <FormField label="Organization name" htmlFor="org-name" error={errors.name?.message}>
            <Input id="org-name" placeholder="e.g. Acme Inc" autoFocus {...register("name")} />
          </FormField>
          <div className="flex gap-2">
            <Button type="submit" disabled={create.isPending}>
              Create organization
            </Button>
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
