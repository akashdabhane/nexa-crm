import { createResourceHooks } from "@/hooks/use-resource";
import { companiesService } from "@/services/companies";

export const companyHooks = createResourceHooks("companies", companiesService, {
  label: "Company",
  related: ["contacts", "deals"],
});
