"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { ListParams, Paginated } from "@/types";

type Service<T, TInput> = {
  list: (params?: ListParams) => Promise<Paginated<T>>;
  get: (id: string) => Promise<T>;
  create: (data: TInput) => Promise<T>;
  update: (id: string, data: Partial<TInput>) => Promise<T>;
  remove: (id: string) => Promise<void>;
};

/**
 * TanStack Query hooks for one REST resource.
 * `key` is the cache namespace, e.g. "contacts". `related` lists other
 * namespaces whose data changes when this one does (e.g. companies show
 * contact counts), so they are refetched after a mutation.
 */
export function createResourceHooks<T, TInput>(
  key: string,
  service: Service<T, TInput>,
  { label, related = [] }: { label: string; related?: string[] },
) {
  function useInvalidate() {
    const queryClient = useQueryClient();
    return () =>
      Promise.all(
        [key, ...related, "dashboard", "timeline"].map((k) => queryClient.invalidateQueries({ queryKey: [k] })),
      );
  }

  return {
    useList(params: ListParams, options: { enabled?: boolean } = {}) {
      return useQuery({
        queryKey: [key, "list", params],
        queryFn: () => service.list(params),
        placeholderData: keepPreviousData, // keep the old page visible while the next one loads
        ...options,
      });
    },

    useOne(id: string | undefined) {
      return useQuery({ queryKey: [key, "detail", id], queryFn: () => service.get(id!), enabled: Boolean(id) });
    },

    useCreate() {
      const invalidate = useInvalidate();
      return useMutation({
        mutationFn: service.create,
        onSuccess: () => {
          toast.success(`${label} created`);
          return invalidate();
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      });
    },

    useUpdate() {
      const invalidate = useInvalidate();
      return useMutation({
        mutationFn: ({ id, data }: { id: string; data: Partial<TInput> }) => service.update(id, data),
        onSuccess: () => {
          toast.success(`${label} updated`);
          return invalidate();
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      });
    },

    useDelete() {
      const invalidate = useInvalidate();
      return useMutation({
        mutationFn: service.remove,
        onSuccess: () => {
          toast.success(`${label} deleted`);
          return invalidate();
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      });
    },
  };
}
