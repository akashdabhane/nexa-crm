import { api } from "@/lib/api-client";
import type { Profile, UserRole } from "@/types";

export const usersService = {
  me: () => api.get<Profile>("/me").then((r) => r.data),
  updateMe: (data: { full_name: string }) => api.patch<Profile>("/me", data).then((r) => r.data),
  list: () => api.get<Profile[]>("/users").then((r) => r.data),
  update: (id: string, data: { role?: UserRole; is_active?: boolean }) =>
    api.patch<Profile>(`/users/${id}`, data).then((r) => r.data),
};
