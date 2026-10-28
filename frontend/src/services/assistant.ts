import { api } from "@/lib/api-client";
import type { AssistantMessage, AssistantReply } from "@/types";

export const assistantService = {
  /** Sends the whole conversation; the backend keeps no chat state. */
  chat: (messages: AssistantMessage[]) =>
    api.post<AssistantReply>("/assistant/chat", { messages }).then((r) => r.data),
};
