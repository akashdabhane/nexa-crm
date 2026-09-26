import { api } from "@/lib/api-client";
import type { Company, CompanyInput } from "@/types";

import { createCrudService } from "./crud";

export const companiesService = {
  ...createCrudService<Company, CompanyInput>("/companies"),
  industries: () => api.get<string[]>("/companies/industries").then((r) => r.data),
};
