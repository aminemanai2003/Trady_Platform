"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, BookOpen, Sparkles, FileText, AlertCircle } from "lucide-react";
import { RBButton } from "@/components/reactbits";

interface Message {
    id:        string;
    role:      "user" | "assistant";
    text:      string;
    sources:   string[];
    cached:    boolean;
    error:     boolean;
    streaming: boolean;
}

interface Props {
    hasDocs: boolean;
}

function uid() {
    return Math.random().toString(36).slice(2);
}

export default function QueryChat({ hasDocs }: Props) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [query,    setQuery]    = useState("");
    const [busy,     setBusy]     = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function handleSend() {
        const q = query.trim();
        if (!q || busy) return;

        const userMsg: Message = {
            id: uid(), role: "user", text: q,
            sources: [], cached: false, error: false, streaming: false,
        };
        setMessages((prev) => [...prev, userMsg]);
        setQuery("");
        setBusy(true);

        const assistantId = uid();
        setMessages((prev) => [
            ...prev,
            { id: assistantId, role: "assistant", text: "", sources: [], cached: false, error: false, streaming: true },
        ]);

        try {
            const res = await fetch("/api/rag/stream", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ query: q }),
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

            const reader  = res.body.getReader();
            const decoder = new TextDecoder();
            let   buffer  = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const payload = JSON.parse(line.slice(6)) as {
                            token?: string;
                            done?: boolean;
                            sources?: string[];
                            provider?: string;
                        };

                        if (payload.token) {
                            setMessages((prev) => prev.map((m) =>
                                m.id === assistantId
                                    ? { ...m, text: m.text + payload.token }
                                    : m
                            ));
                        }

                        if (payload.done) {
                            setMessages((prev) => prev.map((m) =>
                                m.id === assistantId
                                    ? { ...m, sources: payload.sources ?? [], streaming: false }
                                    : m
                            ));
                        }
                    } catch {
                        // skip malformed SSE line
                    }
                }
            }
        } catch {
            setMessages((prev) => prev.map((m) =>
                m.id === assistantId
                    ? { ...m, text: "Network error. Could not reach the server.", error: true, streaming: false }
                    : m
            ));
        } finally {
            setBusy(false);
        }
    }

    function handleKey(e: React.KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSend();
        }
    }

    return (
        <div className="flex flex-col h-full min-h-[420px]">
            {/* Conversation area */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-2">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full py-12 text-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-violet-600/20 flex items-center justify-center">
                            <BookOpen className="size-6 text-violet-400" />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-300">Strategy Tutor</p>
                            <p className="text-xs text-slate-500 mt-1 max-w-xs">
                                {hasDocs
                                    ? "Ask any question about your uploaded trading documents."
                                    : "Upload a trading document first, then ask questions about it."}
                            </p>
                        </div>

                        {hasDocs && (
                            <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
                                {[
                                    "Explain what a liquidity grab is",
                                    "What is the difference between support and resistance?",
                                    "How does the RSI indicator work?",
                                ].map((suggestion) => (
                                    <button
                                        key={suggestion}
                                        type="button"
                                        onClick={() => setQuery(suggestion)}
                                        className="text-left text-xs px-3 py-2 rounded-lg border border-slate-700 bg-slate-800/60 text-slate-400 hover:border-sky-500/50 hover:text-sky-300 transition-colors"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`
                                max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed
                                ${msg.role === "user"
                                    ? "bg-sky-600 text-white rounded-br-sm"
                                    : msg.error
                                    ? "bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-bl-sm"
                                    : "bg-slate-800 text-slate-200 border border-slate-700/60 rounded-bl-sm"
                                }
                            `}
                        >
                            {msg.role === "assistant" && !msg.error && (
                                <div className="flex items-center gap-1.5 mb-2 text-xs text-violet-400">
                                    <Sparkles className="size-3" />
                                    <span>Strategy Tutor</span>
                                </div>
                            )}
                            {msg.role === "assistant" && msg.error && (
                                <div className="flex items-center gap-1.5 mb-1.5 text-xs">
                                    <AlertCircle className="size-3 text-rose-400" />
                                    <span className="text-rose-400">Error</span>
                                </div>
                            )}

                            <p className="whitespace-pre-wrap">
                                {msg.text}
                                {msg.streaming && (
                                    <span className="inline-block w-0.5 h-[1em] bg-violet-400 animate-pulse ml-0.5 align-middle" />
                                )}
                            </p>

                            {msg.sources.length > 0 && (
                                <div className="mt-2.5 pt-2 border-t border-slate-700/50">
                                    <p className="text-xs text-slate-500 mb-1.5 flex items-center gap-1">
                                        <FileText className="size-3" /> Sources
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {msg.sources.map((src) => (
                                            <span
                                                key={src}
                                                className="text-xs bg-slate-700/60 text-slate-400 rounded px-2 py-0.5"
                                            >
                                                {src}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="relative mt-3">
                <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKey}
                    disabled={busy || !hasDocs}
                    placeholder={
                        !hasDocs
                            ? "Upload a document first to ask questions…"
                            : "Ask about your documents… (Enter to send)"
                    }
                    rows={2}
                    className="w-full resize-none rounded-xl bg-slate-800 border border-slate-600 px-4 py-3 pr-14 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
                />
                <RBButton
                    className="absolute right-2 bottom-2 !p-2 !h-auto"
                    onClick={() => void handleSend()}
                    disabled={!query.trim() || busy || !hasDocs}
                    title="Send"
                >
                    {busy
                        ? <Loader2 className="size-4 animate-spin" />
                        : <Send className="size-4" />
                    }
                </RBButton>
            </div>

            <p className="text-xs text-slate-600 text-center mt-2">
                Educational use only — not financial advice · Powered by local AI
            </p>
        </div>
    );
}

