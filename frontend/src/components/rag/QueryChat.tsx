"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Database, Trash2 } from "lucide-react";
import {
    RagComposer,
    RagMessage,
    RagMessageAction,
    RagSourceList,
    RagSource,
    RagSuggestedPrompts,
    RagThinkingDots,
    RagThread,
} from "@/components/rag/rag-ui";

interface Message {
    id: string;
    role: "user" | "assistant";
    text: string;
    sources: RagSource[];
    cached: boolean;
    error: boolean;
    streaming: boolean;
    prompt?: string;
}

interface Props {
    hasDocs: boolean;
}

const SUGGESTED_PROMPTS = [
    "Summarize all uploaded strategy rules.",
    "What does the image say about risk?",
    "What did the audio/video mention about sessions?",
    "Which sources support this answer?",
];

function uid() {
    return Math.random().toString(36).slice(2);
}

export default function QueryChat({ hasDocs }: Props) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [query, setQuery] = useState("");
    const [busy, setBusy] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function streamAssistantResponse(q: string, assistantId: string) {
        let completed = false;
        try {
            const res = await fetch("/api/rag/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: q }),
            });

            if (!res.ok || !res.body) {
                const data = await res.json().catch(() => ({}));
                setMessages((prev) => prev.map((m) =>
                    m.id === assistantId
                        ? { ...m, text: data.error ?? "Request failed.", error: true, streaming: false }
                        : m
                ));
                return;
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            const handleSseLine = (line: string) => {
                if (!line.startsWith("data: ")) return;
                try {
                    const payload = JSON.parse(line.slice(6)) as {
                        token?: string;
                        done?: boolean;
                        sources?: RagSource[];
                        cached?: boolean;
                    };

                    if (payload.token) {
                        setMessages((prev) => prev.map((m) =>
                            m.id === assistantId
                                ? { ...m, text: m.text + payload.token }
                                : m
                        ));
                    }

                    if (payload.done) {
                        completed = true;
                        setMessages((prev) => prev.map((m) =>
                            m.id === assistantId
                                ? {
                                    ...m,
                                    sources: payload.sources ?? [],
                                    cached: Boolean(payload.cached),
                                    streaming: false,
                                }
                                : m
                        ));
                    }
                } catch {
                    // Skip malformed SSE line.
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    if (buffer.trim()) {
                        for (const line of buffer.split("\n")) {
                            handleSseLine(line.trimEnd());
                        }
                    }
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";
                for (const line of lines) {
                    handleSseLine(line.trimEnd());
                }
            }
        } catch {
            setMessages((prev) => prev.map((m) =>
                m.id === assistantId
                    ? { ...m, text: "Network error. Could not reach the server.", error: true, streaming: false }
                    : m
            ));
        } finally {
            if (!completed) {
                setMessages((prev) => prev.map((m) =>
                    m.id === assistantId ? { ...m, streaming: false } : m
                ));
            }
            setBusy(false);
        }
    }

    async function runQuery(rawQuery: string) {
        const q = rawQuery.trim();
        if (!q || busy) return;

        const userMsg: Message = {
            id: uid(),
            role: "user",
            text: q,
            sources: [],
            cached: false,
            error: false,
            streaming: false,
        };
        const assistantId = uid();

        setMessages((prev) => [
            ...prev,
            userMsg,
            {
                id: assistantId,
                role: "assistant",
                text: "",
                sources: [],
                cached: false,
                error: false,
                streaming: true,
                prompt: q,
            },
        ]);
        setQuery("");
        setBusy(true);
        await streamAssistantResponse(q, assistantId);
    }

    async function copyMessage(text: string) {
        await navigator.clipboard.writeText(text).catch(() => undefined);
    }

    function regenerate(msg: Message) {
        if (!msg.prompt || busy) return;
        setMessages((prev) => prev.map((m) =>
            m.id === msg.id
                ? { ...m, text: "", sources: [], cached: false, error: false, streaming: true }
                : m
        ));
        setBusy(true);
        void streamAssistantResponse(msg.prompt, msg.id);
    }

    return (
        <div className="flex h-full min-h-[560px] flex-col">
            <RagThread>
                {messages.length === 0 && (
                    <div className="mx-auto flex min-h-[360px] max-w-2xl flex-col items-center justify-center gap-5 py-10 text-center">
                        <div className="flex size-14 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-400/10 text-violet-200 shadow-[0_0_40px_rgba(139,92,246,0.12)]">
                            <Database className="size-7" />
                        </div>
                        <div>
                            <p className="text-base font-semibold text-foreground">Ask your knowledge base</p>
                            <p className="mt-2 text-sm leading-6 text-slate-500">
                                Query text, images, audio, and video with cited evidence.
                            </p>
                        </div>
                        {hasDocs ? (
                            <RagSuggestedPrompts prompts={SUGGESTED_PROMPTS} onSelect={(prompt) => void runQuery(prompt)} />
                        ) : (
                            <div className="rounded-xl border border-border bg-muted/55 px-4 py-3 text-sm text-muted-foreground">
                                Upload knowledge first, then the tutor can cite exact sources.
                            </div>
                        )}
                    </div>
                )}

                {messages.map((msg) => (
                    <RagMessage
                        key={msg.id}
                        role={msg.role}
                        streaming={msg.streaming}
                        error={msg.error}
                        actions={
                            msg.role === "assistant" && !msg.streaming ? (
                                <>
                                    <RagMessageAction label="Copy" icon="copy" onClick={() => void copyMessage(msg.text)} />
                                    {msg.prompt && (
                                        <RagMessageAction label="Regenerate" icon="regenerate" onClick={() => regenerate(msg)} />
                                    )}
                                </>
                            ) : null
                        }
                    >
                        {msg.error && (
                            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-rose-300">
                                <AlertCircle className="size-3.5" />
                                Error
                            </div>
                        )}
                        {msg.streaming && !msg.text ? (
                            <RagThinkingDots />
                        ) : (
                            <p className="whitespace-pre-wrap">{msg.text}</p>
                        )}
                        <RagSourceList sources={msg.sources} />
                    </RagMessage>
                ))}
                <div ref={bottomRef} />
            </RagThread>

            {messages.length > 0 && (
                <div className="mx-auto mb-2 flex w-full max-w-4xl justify-end gap-1 px-1">
                    <button
                        type="button"
                        onClick={() => setMessages([])}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-40"
                    >
                        <Trash2 className="size-3.5" />
                        Clear
                    </button>
                </div>
            )}

            <RagComposer
                value={query}
                onChange={setQuery}
                onSubmit={() => void runQuery(query)}
                disabled={busy || !hasDocs}
                busy={busy}
                placeholder={!hasDocs ? "Upload a document first to ask questions..." : "Ask about your documents..."}
            />

            <p className="mt-2 text-center text-xs text-slate-600">
                Educational use only - not financial advice
            </p>
        </div>
    );
}
