"use client";

import {
  Activity,
  Building2,
  Check,
  CheckSquare,
  Loader2,
  Mic,
  RotateCcw,
  SendHorizontal,
  Sparkles,
  StickyNote,
  Target,
  User,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { getErrorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { entityHref } from "@/services/notifications";
import type { AssistantMessage, AssistantRecord } from "@/types";

import { useAssistantChat, useTranscribe } from "./hooks";
import { microphoneErrorMessage, useVoiceRecorder } from "./use-voice-recorder";
import { VoiceLevel } from "./voice-level";

function formatDuration(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

const RECORD_ICONS: Record<AssistantRecord["type"], LucideIcon> = {
  lead: Target,
  contact: User,
  company: Building2,
  activity: Activity,
  note: StickyNote,
  task: CheckSquare,
};

const SUGGESTIONS = [
  "Cold-called Priya Shah, CTO at Brightwave. She's interested in a demo next week.",
  "Got a reply to my cold email from Tom Becker at Nordic Freight — he wants pricing by Friday.",
  "Met Lena from Acme at a conference; budget approved for Q1. Follow up on Monday.",
];

/**
 * Chat with the AI assistant, available from the top bar on every page. The conversation lives in this
 * component (always mounted in the layout), so it survives closing the panel and navigating between pages.
 */
export function AssistantSheet() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState("");
  const chat = useAssistantChat();
  const transcription = useTranscribe();
  const recorder = useVoiceRecorder({ onLimit: () => finishVoice("review") });
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const transcribing = transcription.isPending;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chat.isPending]);

  // While recording: Enter sends what was said, Escape discards it (like the chat box's own Enter).
  useEffect(() => {
    if (!recorder.recording) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        finishVoice("send");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  async function startVoice() {
    try {
      await recorder.start();
    } catch (error) {
      toast.error(microphoneErrorMessage(error));
    }
  }

  /** Stop recording and turn it into text: sent straight away, or put in the box to check and edit first. */
  async function finishVoice(then: "send" | "review") {
    const audio = await recorder.stop();
    if (!audio) return;
    transcription.mutate(audio, {
      onSuccess: (text) => {
        if (!text) {
          toast.info("I didn't catch that. Try again, a little closer to the microphone.");
          return;
        }
        const message = draft.trim() ? `${draft.trim()} ${text}` : text;
        if (then === "send" && !chat.isPending) {
          send(message);
        } else {
          setDraft(message);
          textareaRef.current?.focus();
        }
      },
      onError: (error) => toast.error(getErrorMessage(error, "Couldn't turn your recording into text")),
    });
  }

  function send(text: string) {
    const content = text.trim();
    if (!content || chat.isPending) return;
    const conversation: AssistantMessage[] = [...messages, { role: "user", content }];
    setMessages(conversation);
    setDraft("");
    chat.mutate(conversation, {
      onSuccess: (reply) =>
        setMessages([...conversation, { role: "assistant", content: reply.reply, records: reply.records }]),
      onError: (error) => {
        // Put the message back so the user can retry without retyping it.
        setMessages(messages);
        setDraft(content);
        toast.error(getErrorMessage(error, "The assistant couldn't respond"));
      },
    });
  }

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (!next) recorder.cancel(); // never keep listening behind a closed panel
        setOpen(next);
      }}
    >
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Sparkles className="size-4 text-primary" />
          <span className="hidden sm:inline">AI Assistant</span>
        </Button>
      </SheetTrigger>
      <SheetContent
        className="gap-0 p-0 data-[side=right]:w-full data-[side=right]:sm:max-w-md"
        onEscapeKeyDown={(event) => {
          // Escape while recording cancels the recording, not the whole panel.
          if (recorder.recording) {
            event.preventDefault();
            recorder.cancel();
          }
        }}
      >
        <SheetHeader className="border-b pr-12">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              AI Assistant
            </SheetTitle>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-muted-foreground"
                onClick={() => setMessages([])}
                disabled={chat.isPending}
              >
                <RotateCcw className="size-3.5" />
                New chat
              </Button>
            )}
          </div>
          <SheetDescription>
            Tell me about your calls, emails and new prospects in your own words. I&apos;ll save them to the CRM. You
            can also ask me about any lead, contact or company.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Try something like</p>
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setDraft(suggestion)}
                  className="block w-full rounded-lg border p-3 text-left text-sm transition-colors hover:bg-muted/60"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          {messages.map((message, index) => (
            <ChatBubble key={index} message={message} onOpenRecord={() => setOpen(false)} />
          ))}

          {chat.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Working on it…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="space-y-2 border-t p-3">
          <form
            className="flex items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (recorder.recording) finishVoice("send");
              else send(draft);
            }}
          >
            {recorder.recording || transcribing ? (
              <div
                role="status"
                className="flex min-h-10 flex-1 items-center gap-2.5 rounded-md border border-input px-3 text-sm"
              >
                {recorder.stream ? (
                  <>
                    <VoiceLevel stream={recorder.stream} />
                    <span>Listening…</span>
                    <span className="ml-auto text-muted-foreground tabular-nums">
                      {formatDuration(recorder.seconds)}
                    </span>
                  </>
                ) : (
                  <>
                    <Loader2 className="size-4 animate-spin text-muted-foreground" />
                    <span className="text-muted-foreground">Turning your voice into text…</span>
                  </>
                )}
              </div>
            ) : (
              <Textarea
                ref={textareaRef}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    send(draft);
                  }
                }}
                placeholder="E.g. Cold-called Jane Doe from Acme today…"
                aria-label="Message the AI assistant"
                aria-describedby="assistant-disclaimer"
                className="max-h-40 min-h-10 resize-none"
                maxLength={8000}
                autoFocus
              />
            )}

            {recorder.recording ? (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={recorder.cancel}
                  aria-label="Cancel recording"
                  title="Cancel (Esc)"
                >
                  <X className="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => finishVoice("review")}
                  aria-label="Stop and edit the text before sending"
                  title="Stop and edit before sending"
                >
                  <Check className="size-4" />
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={startVoice}
                disabled={!recorder.supported || transcribing}
                aria-label="Speak your message"
                title={
                  recorder.supported
                    ? "Speak your message"
                    : "Voice input needs a secure (https) page and a browser that can record audio"
                }
              >
                <Mic className="size-4" />
              </Button>
            )}
            <Button
              type="submit"
              size="icon"
              disabled={recorder.recording ? false : !draft.trim() || chat.isPending || transcribing}
              aria-label="Send"
              title={recorder.recording ? "Send what you said (Enter)" : "Send (Enter)"}
            >
              <SendHorizontal className="size-4" />
            </Button>
          </form>
          {recorder.recording && (
            <p className="text-center text-xs text-muted-foreground">
              Press <kbd className="font-medium">Enter</kbd> to send, <Check className="inline size-3" /> to edit the
              text first, or <kbd className="font-medium">Esc</kbd> to cancel.
            </p>
          )}
          <p id="assistant-disclaimer" className="text-center text-xs text-muted-foreground">
            AI can make mistakes. Please cross-check its answers and the records it saves.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function ChatBubble({ message, onOpenRecord }: { message: AssistantMessage; onOpenRecord: () => void }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
      <p
        className={cn(
          "max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap",
          isUser ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-muted",
        )}
      >
        {message.content}
      </p>
      {message.records && message.records.length > 0 && (
        <ul className="w-[85%] space-y-1">
          {message.records.map((record) => (
            <li key={`${record.type}-${record.id}-${record.action}`}>
              <SavedRecordLink record={record} onOpen={onOpenRecord} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SavedRecordLink({ record, onOpen }: { record: AssistantRecord; onOpen: () => void }) {
  const Icon = RECORD_ICONS[record.type];
  const href = entityHref(record.link_type, record.link_id);
  const body = (
    <span className="flex items-center gap-2 rounded-lg border bg-background px-2.5 py-1.5 text-xs">
      <Icon className="size-3.5 shrink-0 text-primary" />
      <span className="min-w-0 flex-1 truncate">{record.label}</span>
      <span className="shrink-0 text-muted-foreground capitalize">
        {record.type} {record.action}
      </span>
    </span>
  );
  return href ? (
    <Link href={href} onClick={onOpen} className="block transition-colors hover:[&>span]:bg-muted/60">
      {body}
    </Link>
  ) : (
    body
  );
}
