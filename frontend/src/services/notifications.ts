import { api } from "@/lib/api-client";
import type { AppNotification, AuditLog, ListParams, Paginated } from "@/types";

export const notificationsService = {
  list: (params: ListParams & { unread_only?: boolean } = {}) =>
    api.get<Paginated<AppNotification>>("/notifications", { params }).then((r) => r.data),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count").then((r) => r.data.count),
  markRead: (id: string) => api.patch<AppNotification>(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => api.post("/notifications/read-all").then(() => undefined),
};

export const auditService = {
  list: (params: ListParams) => api.get<Paginated<AuditLog>>("/audit-logs", { params }).then((r) => r.data),
};

/** Where a notification or audit entry links to in the app. */
export function entityHref(entityType: string | null, entityId: string | null) {
  if (!entityType || !entityId) return null;
  const paths: Record<string, string> = {
    lead: "/leads",
    deal: "/deals",
    contact: "/contacts",
    company: "/companies",
  };
  if (entityType === "task") return "/tasks";
  return paths[entityType] ? `${paths[entityType]}/${entityId}` : null;
}
