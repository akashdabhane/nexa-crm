import { api } from "@/lib/api-client";
import type { Lead, LeadConvertInput, LeadConvertResult, LeadInput } from "@/types";

import { createCrudService } from "./crud";

export const leadsService = {
  ...createCrudService<Lead, LeadInput>("/leads"),
  convert: (id: string, data: LeadConvertInput) =>
    api.post<LeadConvertResult>(`/leads/${id}/convert`, data).then((r) => r.data),
};
