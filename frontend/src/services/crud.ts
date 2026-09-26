import { api } from "@/lib/api-client";
import type { EntityRef, ListParams, Paginated } from "@/types";

/**
 * Typed REST functions for a standard FastAPI resource:
 * GET /path, GET /path/:id, POST /path, PATCH /path/:id, DELETE /path/:id.
 */
export function createCrudService<T, TInput>(path: string) {
  return {
    list: (params: ListParams = {}) => api.get<Paginated<T>>(path, { params }).then((r) => r.data),
    get: (id: string) => api.get<T>(`${path}/${id}`).then((r) => r.data),
    create: (data: TInput) => api.post<T>(path, data).then((r) => r.data),
    update: (id: string, data: Partial<TInput>) => api.patch<T>(`${path}/${id}`, data).then((r) => r.data),
    remove: (id: string) => api.delete(`${path}/${id}`).then(() => undefined),
    /** id/name pairs for select inputs (only for resources exposing /options). */
    options: (params: Record<string, string | undefined> = {}) =>
      api.get<EntityRef[]>(`${path}/options`, { params }).then((r) => r.data),
  };
}

export type CrudService<T, TInput> = ReturnType<typeof createCrudService<T, TInput>>;
