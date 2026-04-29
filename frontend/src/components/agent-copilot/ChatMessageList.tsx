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
      <div className="flex flex-col items-center justify-center py-8 gap-2 text-slate-600">
        <MessageSquare className="size-7 opacity-40" />
        <span className="text-xs">Type to chat, or prefix with /agent for an action.</span>
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
              : "bg-white/[0.05] text-slate-200 border border-white/[0.07] rounded-tl-sm"
          }
        `}
      >
        {content}
        {pending && (
          <span className="ml-0.5 inline-block size-1.5 align-middle rounded-full bg-brand-blue-400 animate-pulse" />
        )}
      </div>
      {isUser && (
        <div className="size-6 shrink-0 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mt-0.5">
          <User className="size-3 text-slate-400" />
        </div>
      )}
    </div>
  );
}
