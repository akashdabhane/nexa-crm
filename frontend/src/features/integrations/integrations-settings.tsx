"use client";

import { AlertTriangle, Copy, Pencil, Plus, RefreshCw, RotateCcw, Trash2, Webhook } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PLATFORM_LABELS, PlatformIcon } from "@/components/shared/platform-badge";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { metaWebhookUrl, webhookUrl } from "@/services/integrations";
import type { LeadIntegration } from "@/types";
import { formatDateTime } from "@/utils/format";

import {
  useDeleteIntegration,
  useIntegrations,
  useIntegrationSetup,
  useRotateToken,
  useSyncIntegration,
  useUpdateIntegration,
} from "./hooks";
import { IntegrationFormDialog } from "./integration-form-dialog";

const SAMPLE_PAYLOAD = `{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1 555 0100",
  "company": "Acme",
  "username": "@janedoe",
  "id": "platform-lead-id-123",
  "message": "Interested in a demo"
}`;

function CopyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Input readOnly value={value} aria-label={label} className="h-8 min-w-0 font-mono text-xs" onFocus={(e) => e.target.select()} />
      <Button
        size="icon"
        variant="outline"
        className="size-8 shrink-0"
        aria-label={`Copy ${label}`}
        onClick={() => navigator.clipboard.writeText(value).then(() => toast.success("Copied"))}
      >
        <Copy />
      </Button>
    </div>
  );
}

function IntegrationRow({ integration, onEdit }: { integration: LeadIntegration; onEdit: () => void }) {
  const update = useUpdateIntegration();
  const sync = useSyncIntegration();
  const rotate = useRotateToken();
  const remove = useDeleteIntegration();
  const [confirm, setConfirm] = useState<"delete" | "rotate" | null>(null);
  const isMeta = integration.kind === "meta_lead_ads";

  return (
    <div className="grid gap-3 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {isMeta ? (
            <span className="flex -space-x-1.5 pt-0.5">
              <PlatformIcon platform="facebook" className="size-7 ring-2 ring-background" />
              <PlatformIcon platform="instagram" className="size-7 ring-2 ring-background" />
            </span>
          ) : (
            <PlatformIcon platform={integration.platform} className="mt-0.5 size-7" />
          )}
          <div className="min-w-0">
            <p className="font-medium">{integration.name}</p>
            <p className="text-xs text-muted-foreground">
              {isMeta
                ? `Meta Lead Ads · Page ${integration.meta_page_name ?? integration.meta_page_id}`
                : `Webhook · ${PLATFORM_LABELS[integration.platform]}`}
              {" · "}
              {integration.leads_imported} lead{integration.leads_imported === 1 ? "" : "s"} imported
              {integration.last_lead_at && ` · last ${formatDateTime(integration.last_lead_at)}`}
              {integration.default_owner && ` · assigned to ${integration.default_owner.full_name}`}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Switch
            checked={integration.is_active}
            onCheckedChange={(checked) => update.mutate({ id: integration.id, data: { is_active: checked } })}
            aria-label={`${integration.name} active`}
          />
          {isMeta && (
            <Button size="sm" variant="outline" onClick={() => sync.mutate(integration.id)} disabled={sync.isPending}>
              <RefreshCw className={sync.isPending ? "animate-spin" : undefined} /> Sync now
            </Button>
          )}
          <Button size="icon" variant="ghost" className="size-8" aria-label={`Edit ${integration.name}`} onClick={onEdit}>
            <Pencil />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-8 text-destructive"
            aria-label={`Remove ${integration.name}`}
            onClick={() => setConfirm("delete")}
          >
            <Trash2 />
          </Button>
        </div>
      </div>

      {integration.last_error && (
        <p className="flex items-start gap-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {integration.last_error}
        </p>
      )}
      {isMeta && integration.last_synced_at && (
        <p className="text-xs text-muted-foreground">Last synced {formatDateTime(integration.last_synced_at)}</p>
      )}

      {!isMeta && (
        <div className="grid gap-1.5">
          <p className="text-xs font-medium text-muted-foreground">Send leads (POST JSON) to this secret URL</p>
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1">
              <CopyField label="webhook URL" value={webhookUrl(integration.webhook_token)} />
            </div>
            <Button size="sm" variant="ghost" onClick={() => setConfirm("rotate")}>
              <RotateCcw /> New URL
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirm === "delete"}
        onOpenChange={(open) => !open && setConfirm(null)}
        title="Remove this lead source?"
        description={`New leads from “${integration.name}” will stop arriving. Leads already imported stay in the CRM.`}
        confirmLabel="Remove"
        isPending={remove.isPending}
        onConfirm={() => remove.mutate(integration.id, { onSuccess: () => setConfirm(null) })}
      />
      <ConfirmDialog
        open={confirm === "rotate"}
        onOpenChange={(open) => !open && setConfirm(null)}
        title="Create a new webhook URL?"
        description="The current URL stops working immediately; update it in Zapier/Make or wherever you use it."
        confirmLabel="Create new URL"
        destructive={false}
        isPending={rotate.isPending}
        onConfirm={() => rotate.mutate(integration.id, { onSuccess: () => setConfirm(null) })}
      />
    </div>
  );
}

export function IntegrationsSettings() {
  const { data: integrations, isLoading, error, refetch } = useIntegrations();
  const { data: setup } = useIntegrationSetup();
  const [editing, setEditing] = useState<LeadIntegration | null>(null);
  const [creating, setCreating] = useState(false);

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
          <div className="grid gap-1.5">
            <CardTitle>Social lead sources</CardTitle>
            <CardDescription>
              Bring leads in from social media automatically. New leads are created with status “New”, tagged with their platform,
              de-duplicated by email and lead id, and assigned to the owner you choose (who gets a notification).
            </CardDescription>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus /> Connect source
          </Button>
        </CardHeader>
        <CardContent>
          {error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : isLoading ? (
            <Skeleton className="h-32" />
          ) : integrations?.length ? (
            <div className="divide-y">
              {integrations.map((integration) => (
                <IntegrationRow key={integration.id} integration={integration} onEdit={() => setEditing(integration)} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Webhook}
              title="No lead sources yet"
              description="Connect a Facebook Page for Facebook & Instagram lead ads, or create a webhook for X, LinkedIn, TikTok and others."
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How to connect each platform</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 text-sm">
          <section className="grid gap-2">
            <h3 className="flex items-center gap-2 font-medium">
              <PlatformIcon platform="facebook" /> <PlatformIcon platform="instagram" /> Facebook &amp; Instagram lead ads (Meta)
            </h3>
            <ol className="ml-5 list-decimal space-y-1 text-muted-foreground">
              <li>
                Create an app at developers.facebook.com, add the Webhooks product, subscribe to the <b>Page</b> object&apos;s{" "}
                <b>leadgen</b> field with the callback URL below and your <code>META_VERIFY_TOKEN</code>.
              </li>
              <li>
                Generate a long-lived <b>Page access token</b> (permissions: leads_retrieval, pages_manage_metadata,
                pages_show_list, pages_read_engagement, ads_management) and click “Connect source”.
              </li>
              <li>Instagram lead forms run through the Facebook Page linked to the Instagram account, so one connection covers both.</li>
              <li>“Sync now” pulls leads that arrived before the connection (and any missed webhook).</li>
            </ol>
            <CopyField label="Meta callback URL" value={metaWebhookUrl()} />
            {setup && (!setup.meta_webhook_ready || !setup.token_storage_ready) && (
              <p className="flex items-start gap-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                Server setup missing:{" "}
                {[
                  !setup.meta_webhook_ready && "META_APP_SECRET and META_VERIFY_TOKEN (real-time webhooks)",
                  !setup.token_storage_ready && "INTEGRATIONS_SECRET (needed to save Page tokens)",
                ]
                  .filter(Boolean)
                  .join("; ")}
                . Add them to backend/.env and restart the API.
              </p>
            )}
          </section>

          <section className="grid gap-2">
            <h3 className="flex items-center gap-2 font-medium">
              <PlatformIcon platform="twitter" /> <PlatformIcon platform="linkedin" /> <PlatformIcon platform="tiktok" />
              <PlatformIcon platform="youtube" /> X, LinkedIn, TikTok, YouTube and others (webhook)
            </h3>
            <p className="text-muted-foreground">
              These platforms don&apos;t offer an open lead API, so connect them through an automation tool: in Zapier, Make or
              n8n use the platform&apos;s lead trigger (e.g. “LinkedIn Lead Gen Forms – New Lead”, “TikTok Lead Generation – New
              Lead”, or a new DM/mention on X) with a “Webhook – POST” action to the integration&apos;s URL. Send JSON like:
            </p>
            <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">{SAMPLE_PAYLOAD}</pre>
            <p className="text-muted-foreground">
              A list of such objects (or <code>{"{ \"leads\": [...] }"}</code>, up to 100) also works. Field names are matched
              loosely (first_name + last_name, phone_number, company_name…); extra fields become a note on the lead.
            </p>
          </section>

          <section className="grid gap-1">
            <h3 className="font-medium">One-off exports</h3>
            <p className="text-muted-foreground">
              Downloaded a CSV from Meta Leads Center, LinkedIn Campaign Manager or TikTok? Use <b>Leads → Import</b>.
            </p>
          </section>
        </CardContent>
      </Card>

      <IntegrationFormDialog open={creating} onOpenChange={setCreating} />
      <IntegrationFormDialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)} integration={editing ?? undefined} />
    </div>
  );
}
