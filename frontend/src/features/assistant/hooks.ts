import { useMutation, useQueryClient } from "@tanstack/react-query";

import { assistantService } from "@/services/assistant";

export function useAssistantChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: assistantService.chat,
    // The assistant may have touched any list, detail, timeline or dashboard: refetch what's on screen.
    onSuccess: (reply) => {
      if (reply.records.length > 0) queryClient.invalidateQueries();
    },
  });
}
