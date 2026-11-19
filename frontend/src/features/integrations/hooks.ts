import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import { integrationsService } from "@/services/integrations";
import type { ImportResult, LeadIntegrationInput } from "@/types";

const KEY = "integrations";

export function importSummary({ created, skipped, failed }: ImportResult): string {
  const parts = [`${created} lead${created === 1 ? "" : "s"} imported`];
  if (skipped) parts.push(`${skipped} duplicate${skipped === 1 ? "" : "s"} skipped`);
  if (failed) parts.push(`${failed} row${failed === 1 ? "" : "s"} couldn't be read`);
  return parts.join(", ");
}

export function useIntegrations() {
  return useQuery({ queryKey: [KEY, "list"], queryFn: integrationsService.list });
}

export function useIntegrationSetup() {
  return useQuery({ queryKey: [KEY, "setup"], queryFn: integrationsService.setup, staleTime: Infinity });
}

function useIntegrationMutation<TArgs, TResult>(
  mutationFn: (args: TArgs) => Promise<TResult>,
  success: string | ((result: TResult) => string),
  invalidateLeads = false,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (result) => {
      toast.success(typeof success === "string" ? success : success(result));
      const keys = invalidateLeads ? [KEY, "leads", "dashboard", "notifications"] : [KEY];
      return Promise.all(keys.map((key) => queryClient.invalidateQueries({ queryKey: [key] })));
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useCreateIntegration() {
  return useIntegrationMutation(integrationsService.create, "Integration added");
}

export function useUpdateIntegration() {
  return useIntegrationMutation(
    ({ id, data }: { id: string; data: LeadIntegrationInput }) => integrationsService.update(id, data),
    "Integration updated",
  );
}

export function useDeleteIntegration() {
  return useIntegrationMutation(integrationsService.remove, "Integration removed");
}

export function useRotateToken() {
  return useIntegrationMutation(integrationsService.rotateToken, "New webhook URL created; update it in your tools");
}

export function useSyncIntegration() {
  return useIntegrationMutation(integrationsService.sync, importSummary, true);
}
