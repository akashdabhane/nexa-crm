import { api, withoutOrganization } from "@/lib/api-client";
import type { Invitation, MyInvitation, MyOrganization, Organization, Profile, UserRole } from "@/types";

export const organizationsService = {
  // Account level: not tied to the active organization.
  me: () => api.get<Profile>("/me", withoutOrganization).then((r) => r.data),
  mine: () => api.get<MyOrganization[]>("/organizations", withoutOrganization).then((r) => r.data),
  create: (name: string) =>
    api.post<MyOrganization>("/organizations", { name }, withoutOrganization).then((r) => r.data),
  myInvitations: () => api.get<MyInvitation[]>("/me/invitations", withoutOrganization).then((r) => r.data),
  accept: (id: string) =>
    api.post<MyOrganization>(`/me/invitations/${id}/accept`, undefined, withoutOrganization).then((r) => r.data),
  decline: (id: string) =>
    api.post(`/me/invitations/${id}/decline`, undefined, withoutOrganization).then(() => undefined),

  // The active organization.
  current: () => api.get<Organization>("/organizations/current").then((r) => r.data),
  rename: (name: string) => api.patch<Organization>("/organizations/current", { name }).then((r) => r.data),
  invitations: () => api.get<Invitation[]>("/invitations").then((r) => r.data),
  invite: (data: { email: string; role: UserRole }) => api.post<Invitation>("/invitations", data).then((r) => r.data),
  revokeInvitation: (id: string) => api.delete(`/invitations/${id}`).then(() => undefined),
};
