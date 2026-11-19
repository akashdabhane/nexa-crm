import { api } from "@/lib/api-client";
import type { ImportResult, IntegrationSetup, LeadIntegration, LeadIntegrationInput } from "@/types";

export const integrationsService = {
  list: () => api.get<LeadIntegration[]>("/integrations").then((r) => r.data),
  setup: () => api.get<IntegrationSetup>("/integrations/setup").then((r) => r.data),
  create: (data: LeadIntegrationInput) => api.post<LeadIntegration>("/integrations", data).then((r) => r.data),
  update: (id: string, data: LeadIntegrationInput) => api.patch<LeadIntegration>(`/integrations/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/integrations/${id}`).then(() => undefined),
  rotateToken: (id: string) => api.post<LeadIntegration>(`/integrations/${id}/rotate-token`).then((r) => r.data),
  sync: (id: string) => api.post<ImportResult>(`/integrations/${id}/sync`).then((r) => r.data),
};

/** Public URLs the integrations receive leads on (built from the API base URL). */
export function webhookUrl(token: string): string {
  return `${api.defaults.baseURL}/integrations/webhooks/${token}`;
}

export function metaWebhookUrl(): string {
  return `${api.defaults.baseURL}/integrations/meta/webhook`;
}
