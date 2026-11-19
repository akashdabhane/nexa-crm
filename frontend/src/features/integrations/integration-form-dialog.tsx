"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/shared/form-field";
import { PLATFORM_LABELS, PlatformIcon } from "@/components/shared/platform-badge";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SOCIAL_PLATFORMS, type LeadIntegration, type LeadIntegrationInput } from "@/types";

import { useCreateIntegration, useUpdateIntegration } from "./hooks";

const KINDS = ["meta_lead_ads", "webhook"] as const;
const META_PLATFORMS = ["facebook", "instagram"] as const;

const schema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(100),
    kind: z.enum(KINDS),
    platform: z.enum(SOCIAL_PLATFORMS),
    meta_page_id: z.string().trim().regex(/^\d*$/, "Digits only"),
    access_token: z.string().trim().max(2000),
    default_owner_id: z.string().nullable(),
    default_score: z.number({ error: "Enter a score" }).int().min(0, "0–100").max(100, "0–100"),
  })
  .superRefine((values, ctx) => {
    if (values.kind !== "meta_lead_ads") return;
    if (!values.meta_page_id) ctx.addIssue({ code: "custom", path: ["meta_page_id"], message: "Page ID is required" });
  });
type Values = z.infer<typeof schema>;

function toValues(integration?: LeadIntegration): Values {
  return {
    name: integration?.name ?? "",
    kind: integration?.kind ?? "meta_lead_ads",
    platform: integration?.platform ?? "facebook",
    meta_page_id: integration?.meta_page_id ?? "",
    access_token: "",
    default_owner_id: integration?.default_owner?.id ?? null,
    default_score: integration?.default_score ?? 0,
  };
}

type Props = { open: boolean; onOpenChange: (open: boolean) => void; integration?: LeadIntegration };

export function IntegrationFormDialog({ open, onOpenChange, integration }: Props) {
  const create = useCreateIntegration();
  const update = useUpdateIntegration();
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(integration) });
  const kind = useWatch({ control, name: "kind" });
  const isMeta = kind === "meta_lead_ads";
  const platforms = isMeta ? META_PLATFORMS : SOCIAL_PLATFORMS;

  async function onSubmit(values: Values) {
    if (isMeta && !integration && !values.access_token) {
      setError("access_token", { message: "Page access token is required" });
      return;
    }
    const data: LeadIntegrationInput = {
      name: values.name,
      platform: isMeta && !META_PLATFORMS.includes(values.platform as "facebook") ? "facebook" : values.platform,
      default_owner_id: values.default_owner_id,
      default_score: values.default_score,
      ...(isMeta ? { meta_page_id: values.meta_page_id || null } : {}),
      ...(isMeta && values.access_token ? { access_token: values.access_token } : {}),
    };
    try {
      if (integration) await update.mutateAsync({ id: integration.id, data });
      else await create.mutateAsync({ ...data, kind: values.kind });
      onOpenChange(false);
    } catch {
      // Error toast already shown.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{integration ? "Edit lead source" : "Connect a lead source"}</DialogTitle>
          <DialogDescription>
            {isMeta
              ? "Receives leads from Facebook and Instagram lead ads on one Facebook Page, in real time."
              : "Gives you a secret URL. Point Zapier, Make, n8n or your own script at it to send leads from X, LinkedIn, TikTok, YouTube or anywhere else."}
          </DialogDescription>
        </DialogHeader>
        <form id="integration-form" onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
          <FormField label="Type" htmlFor="kind">
            <Controller
              control={control}
              name="kind"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange} disabled={Boolean(integration)}>
                  <SelectTrigger id="kind" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="meta_lead_ads">Meta Lead Ads (Facebook + Instagram)</SelectItem>
                    <SelectItem value="webhook">Webhook (any platform)</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <FormField label="Name" htmlFor="int-name" required error={errors.name?.message}>
            <Input id="int-name" placeholder={isMeta ? "Our Facebook Page" : "Zapier – LinkedIn"} {...register("name")} />
          </FormField>
          <FormField
            label={isMeta ? "Default platform" : "Platform"}
            htmlFor="int-platform"
            hint={isMeta ? "Used if Meta doesn't say where a lead came from." : undefined}
          >
            <Controller
              control={control}
              name="platform"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="int-platform" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {platforms.map((p) => (
                      <SelectItem key={p} value={p}>
                        <PlatformIcon platform={p} /> {PLATFORM_LABELS[p]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
          <FormField label="Lead score (0–100)" htmlFor="int-score" error={errors.default_score?.message}>
            <Input id="int-score" type="number" min={0} max={100} {...register("default_score", { valueAsNumber: true })} />
          </FormField>
          {isMeta && (
            <>
              <FormField label="Facebook Page ID" htmlFor="int-page" required error={errors.meta_page_id?.message}>
                <Input id="int-page" inputMode="numeric" placeholder="1234567890" {...register("meta_page_id")} />
              </FormField>
              <FormField
                label="Page access token"
                htmlFor="int-token"
                required={!integration}
                error={errors.access_token?.message}
                hint={integration?.has_access_token ? "Saved (encrypted). Leave empty to keep it." : "Long-lived token with leads_retrieval."}
              >
                <Input id="int-token" type="password" autoComplete="off" {...register("access_token")} />
              </FormField>
            </>
          )}
          <FormField label="Assign new leads to" htmlFor="int-owner" className="sm:col-span-2" hint="Empty: the admin who set this up.">
            <Controller
              control={control}
              name="default_owner_id"
              render={({ field }) => <UserSelect id="int-owner" value={field.value} onChange={field.onChange} allowEmpty />}
            />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="integration-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : integration ? "Save changes" : "Connect"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
