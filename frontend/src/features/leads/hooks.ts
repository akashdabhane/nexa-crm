import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { createResourceHooks } from "@/hooks/use-resource";
import { getErrorMessage } from "@/lib/api-client";
import { leadsService } from "@/services/leads";
import type { CsvImportInput, LeadConvertInput } from "@/types";

export const leadHooks = createResourceHooks("leads", leadsService, { label: "Lead" });

export function useConvertLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadConvertInput }) => leadsService.convert(id, data),
    onSuccess: () => {
      toast.success("Lead converted");
      // Conversion touches every major entity.
      return queryClient.invalidateQueries();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useImportLeads() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CsvImportInput) => leadsService.importCsv(data),
    onSuccess: (_, data) => {
      if (data.dry_run) return;
      return Promise.all(
        ["leads", "dashboard", "timeline", "notifications"].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
      );
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
