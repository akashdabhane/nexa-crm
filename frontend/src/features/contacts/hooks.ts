import { createResourceHooks } from "@/hooks/use-resource";
import { contactsService } from "@/services/contacts";

export const contactHooks = createResourceHooks("contacts", contactsService, {
  label: "Contact",
  related: ["companies"],
});
