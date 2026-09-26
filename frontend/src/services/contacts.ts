import { api } from "@/lib/api-client";
import type { Contact, ContactInput } from "@/types";

import { createCrudService } from "./crud";

export const contactsService = {
  ...createCrudService<Contact, ContactInput>("/contacts"),
  tags: () => api.get<string[]>("/contacts/tags").then((r) => r.data),
};
