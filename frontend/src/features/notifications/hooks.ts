import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsService } from "@/services/notifications";
import type { ListParams } from "@/types";

/** Polls every 60s; simple and good enough without websockets. */
export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: notificationsService.unreadCount,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useNotifications(params: ListParams & { unread_only?: boolean }) {
  return useQuery({ queryKey: ["notifications", "list", params], queryFn: () => notificationsService.list(params) });
}

function useInvalidateNotifications() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["notifications"] });
}

export function useMarkRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({ mutationFn: notificationsService.markRead, onSuccess: invalidate });
}

export function useMarkAllRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({ mutationFn: notificationsService.markAllRead, onSuccess: invalidate });
}
