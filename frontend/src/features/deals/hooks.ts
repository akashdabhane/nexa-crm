import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { createResourceHooks } from "@/hooks/use-resource";
import { getErrorMessage } from "@/lib/api-client";
import { dealsService, pipelinesService } from "@/services/deals";
import type { DealBoard } from "@/types";

export const dealHooks = createResourceHooks("deals", dealsService, {
  label: "Deal",
  related: ["companies", "board"],
});

export function usePipelines() {
  return useQuery({ queryKey: ["pipelines"], queryFn: pipelinesService.list, staleTime: 5 * 60_000 });
}

/** The default pipeline (first in the list) and its stages. */
export function useDefaultPipeline() {
  const query = usePipelines();
  return { ...query, pipeline: query.data?.[0] };
}

export function useDealBoard(params: { pipeline_id?: string; search?: string; owner_id?: string }) {
  return useQuery({ queryKey: ["board", params], queryFn: () => dealsService.board(params) });
}

/**
 * Move a deal to another stage. The Kanban board updates optimistically, so a
 * dragged card lands immediately; it rolls back if the API rejects the move.
 */
export function useMoveDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ dealId, stageId }: { dealId: string; stageId: string }) => dealsService.move(dealId, stageId),
    onMutate: async ({ dealId, stageId }) => {
      await queryClient.cancelQueries({ queryKey: ["board"] });
      const snapshots = queryClient.getQueriesData<DealBoard>({ queryKey: ["board"] });
      queryClient.setQueriesData<DealBoard>({ queryKey: ["board"] }, (board) => {
        if (!board) return board;
        const deal = board.columns.flatMap((column) => column.deals).find((d) => d.id === dealId);
        if (!deal) return board;
        return {
          ...board,
          columns: board.columns.map((column) => {
            const without = column.deals.filter((d) => d.id !== dealId);
            const leaving = without.length !== column.deals.length;
            if (column.stage.id === stageId) {
              return {
                ...column,
                deals: [{ ...deal, stage: column.stage }, ...without],
                count: column.count + (leaving ? 0 : 1),
                total_value: column.total_value + (leaving ? 0 : deal.value),
              };
            }
            return leaving
              ? { ...column, deals: without, count: column.count - 1, total_value: column.total_value - deal.value }
              : column;
          }),
        };
      });
      return { snapshots };
    },
    onSuccess: (deal) => {
      if (deal.status === "won") toast.success(`🎉 ${deal.name} won!`);
      else toast.success(`Moved to ${deal.stage.name}`);
    },
    onError: (error, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data));
      toast.error(getErrorMessage(error));
    },
    onSettled: () =>
      Promise.all(
        ["board", "deals", "companies", "dashboard", "timeline"].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
      ),
  });
}
