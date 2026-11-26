import { api } from "@/lib/api-client";
import type { AssistantFile, AssistantMessage, AssistantRecordFilters, AssistantReply, ExportFormat } from "@/types";

export const assistantService = {
  /** Sends the whole conversation; the backend keeps no chat state. Earlier files go back by name only. */
  chat: (messages: AssistantMessage[]) =>
    api
      .post<AssistantReply>("/assistant/chat", {
        messages: messages.map(({ files, ...message }) => ({ ...message, files: files?.map((f) => f.filename) })),
      })
      .then((r) => r.data),
  /** Exports a list the assistant offered, without another model call. */
  exportList: ({ filters, format }: { filters: AssistantRecordFilters; format: ExportFormat }) =>
    api.post<AssistantFile>("/assistant/export", { filters, format }).then((r) => r.data),
  /** Sends a voice recording as the raw request body; the backend runs Whisper on it. */
  transcribe: (audio: Blob) =>
    api
      .post<{ text: string }>("/assistant/transcribe", audio, { headers: { "Content-Type": audio.type || "audio/webm" } })
      .then((r) => r.data.text),
};

/** Saves a file the assistant made to the user's downloads. */
export function downloadAssistantFile(file: AssistantFile) {
  const bytes = Uint8Array.from(atob(file.content_base64), (char) => char.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: file.mime_type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = file.filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
