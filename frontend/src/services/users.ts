import { api } from "@/lib/api-client";
import type { Member, Profile, UserRole } from "@/types";

export const usersService = {
  me: () => api.get<Profile>("/me").then((r) => r.data),
  updateMe: (data: { full_name: string }) => api.patch<Profile>("/me", data).then((r) => r.data),
  /** Members of the active organization. */
  list: () => api.get<Member[]>("/users").then((r) => r.data),
  /** Change a member's role, or disable / re-enable their access to the active organization. */
  update: (id: string, data: { role?: UserRole; is_active?: boolean }) =>
    api.patch<Member>(`/users/${id}`, data).then((r) => r.data),
  /** Remove someone from the active organization (their records stay). */
  remove: (id: string) => api.delete(`/users/${id}`).then(() => undefined),
};
