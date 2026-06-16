"use client";

import { useEffect, useRef } from "react";
import { Bot, User, MessageSquare } from "lucide-react";
import type { ChatMessage } from "@/lib/page-agent/chat-client";

interface Props {
  messages: ChatMessage[];
  /** Currently-streaming assistant text (no role yet) */
  streaming?: string | null;
}

export function ChatMessageList({ messages, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex flex-col items-center justify-center px-5 py-12 gap-3 text-center text-muted-foreground">
        <div className="flex size-11 items-center justify-center rounded-xl border border-border bg-muted/60">
          <MessageSquare className="size-5" />
        </div>
        <span className="max-w-[240px] text-xs leading-relaxed">
          Ask a question, or use <span className="font-mono text-foreground">/agent</span> for a guided action.
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 pr-1">
      {messages.map((msg, i) => (
        <Bubble key={i} role={msg.role} content={msg.content} />
      ))}
      {streaming !== null && streaming !== undefined && streaming.length > 0 && (
        <Bubble role="assistant" content={streaming} pending />
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function Bubble({
  role,
  content,
  pending,
}: {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="size-6 shrink-0 rounded-full bg-brand-blue-900/40 border border-brand-blue-700/30 flex items-center justify-center mt-0.5">
          <Bot className="size-3 text-brand-blue-400" />
        </div>
      )}
      <div
        className={`
          max-w-[80%] rounded-2xl px-3 py-2 text-[11.5px] leading-relaxed whitespace-pre-line
          ${
            isUser
              ? "bg-brand-blue-600/80 text-white rounded-tr-sm"
              : "bg-muted/70 text-foreground border border-border rounded-tl-sm"
          }
        `}
      >
        {content}
        {pending && (
          <span className="ml-0.5 inline-block size-1.5 align-middle rounded-full bg-brand-blue-400 animate-pulse" />
        )}
      </div>
      {isUser && (
        <div className="size-6 shrink-0 rounded-full bg-muted border border-border flex items-center justify-center mt-0.5">
          <User className="size-3 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}
