import { api } from "@/lib/api-client";
import type { AssistantMessage, AssistantReply } from "@/types";

export const assistantService = {
  /** Sends the whole conversation; the backend keeps no chat state. */
  chat: (messages: AssistantMessage[]) =>
    api.post<AssistantReply>("/assistant/chat", { messages }).then((r) => r.data),
  /** Sends a voice recording as the raw request body; the backend runs Whisper on it. */
  transcribe: (audio: Blob) =>
    api
      .post<{ text: string }>("/assistant/transcribe", audio, { headers: { "Content-Type": audio.type || "audio/webm" } })
      .then((r) => r.data.text),
};
