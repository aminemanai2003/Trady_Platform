"use client";

/**
 * AgentCopilotPanel — Input router for the Trady Copilot.
 *
 * Pipelines:
 *   /agent <text>  → /api/intent → executeAction(...)
 *   <text>         → /api/chat   → streamed chat bubbles
 *
 * No regex-based intent parsing here: classification is delegated to
 * /api/intent (Ollama Qwen 2.5 3B, temperature 0, strict JSON).
 */

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import type { AgentActivity } from "@page-agent/core";
import {
  Bot,
  X,
  Send,
  Square,
  ChevronDown,
  ChevronUp,
  TerminalSquare,
  CornerDownLeft,
} from "lucide-react";
import { usePageAgent } from "@/hooks/use-page-agent";
import { AgentActivityFeed } from "./AgentActivityFeed";
import { AgentConfirmDialog } from "./AgentConfirmDialog";
import { ChatMessageList } from "./ChatMessageList";
import { fetchIntent, executeAction, type Action } from "@/lib/page-agent/execution-engine";
import { streamChat, type ChatMessage } from "@/lib/page-agent/chat-client";

// ── Mode + slash-command detection ─────────────────────────────────────────

const AGENT_PREFIX = /^\/agent(\s+|$)/i;
const HELP_PREFIX = /^\/(help|\?)\s*$/i;

const HELP_TEXT = [
  "Trady AI Copilot — usage:",
  "",
  "• Type freely → conversational chat (LLaMA 3.2 3B).",
  "• /agent <command> → CLI-style action (Qwen 2.5 3B intent parser).",
  "    Examples:",
  "      /agent take me to login",
  "      /agent open the dashboard",
  "      /agent click the signup button",
  "      /agent run a guided onboarding tour",
  "• /help → this message.",
].join("\n");

// ── Status pill ────────────────────────────────────────────────────────────

type PanelStatus = "idle" | "running" | "completed" | "error";

const STATUS_CONFIG: Record<PanelStatus, { label: string; color: string; pulse: boolean }> = {
  idle: { label: "Ready", color: "bg-slate-500", pulse: false },
  running: { label: "Running", color: "bg-brand-blue-500", pulse: true },
  completed: { label: "Done", color: "bg-emerald-500", pulse: false },
  error: { label: "Error", color: "bg-red-500", pulse: false },
};

// ── Active view: which pipeline owns the body ──────────────────────────────

type ViewMode = "chat" | "agent";

// ── Component ──────────────────────────────────────────────────────────────

export function AgentCopilotPanel() {
  const router = useRouter();
  const { status: agentStatus, activities, execute, stop, clearActivities } = usePageAgent();

  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [view, setView] = useState<ViewMode>("chat");

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [streamingReply, setStreamingReply] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatAbortRef = useRef<AbortController | null>(null);

  // Agent-pipeline state (synthetic activities for instant NAV / UI / UNKNOWN)
  const [syntheticActivities, setSyntheticActivities] = useState<AgentActivity[]>([]);
  const [agentRunning, setAgentRunning] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  // ── Cleanup on unmount ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      chatAbortRef.current?.abort();
    };
  }, []);

  // ── Effective status ─────────────────────────────────────────────────────

  const isPageAgentBusy = agentStatus === "running";
  const anythingRunning = chatLoading || agentRunning || isPageAgentBusy;

  const panelStatus: PanelStatus = useMemo(() => {
    if (anythingRunning) return "running";
    if (chatError) return "error";
    if (agentStatus === "completed") return "completed";
    return "idle";
  }, [anythingRunning, chatError, agentStatus]);

  const statusCfg = STATUS_CONFIG[panelStatus];

  // ── Pipeline: CHAT ───────────────────────────────────────────────────────

  const runChat = useCallback(async (userText: string) => {
    setChatError(null);
    setView("chat");

    const nextHistory: ChatMessage[] = [
      ...chatMessages,
      { role: "user", content: userText },
    ];
    setChatMessages(nextHistory);
    setStreamingReply("");

    const abort = new AbortController();
    chatAbortRef.current?.abort();
    chatAbortRef.current = abort;
    setChatLoading(true);

    try {
      let acc = "";
      await streamChat(
        nextHistory,
        {
          onDelta: (d) => {
            acc += d;
            setStreamingReply(acc);
          },
          onDone: (full) => {
            const final = full || acc;
            setChatMessages((prev) => [...prev, { role: "assistant", content: final }]);
            setStreamingReply(null);
          },
          onError: (err) => {
            console.error("[Copilot] chat stream error:", err);
            setChatError(err.message);
            setStreamingReply(null);
          },
        },
        abort.signal
      );
    } catch (err) {
      // streamChat already routed error through onError; nothing to do
      console.warn("[Copilot] chat aborted/errored:", err);
    } finally {
      setChatLoading(false);
    }
  }, [chatMessages]);

  // ── Pipeline: AGENT ──────────────────────────────────────────────────────

  const pushSyntheticAction = useCallback((label: string, ok: boolean, message: string) => {
    setSyntheticActivities([
      { type: "thinking" } as AgentActivity,
      {
        type: "executing",
        tool: "intent_classifier",
        input: { label },
      } as AgentActivity,
      {
        type: "executed",
        tool: ok ? "done" : "error",
        input: { label },
        output: message,
        duration: 0,
      } as AgentActivity,
    ]);
  }, []);

  const runAgent = useCallback(
    async (rawCommand: string) => {
      setView("agent");
      setSyntheticActivities([{ type: "thinking" } as AgentActivity]);
      setAgentRunning(true);
      clearActivities();

      try {
        const action: Action = await fetchIntent(rawCommand);
        console.log(`[Copilot] /agent → action=${action.type}`, action);

        // For AGENT_TASK we hand off to the page-agent loop; the activity feed
        // takes over and the synthetic feed clears so we don't duplicate.
        if (action.type === "AGENT_TASK") {
          setSyntheticActivities([]);
          await executeAction(action, {
            router,
            runPageAgent: (task) => execute(task),
          });
          return;
        }

        const result = await executeAction(action, {
          router,
          runPageAgent: (task) => execute(task),
        });
        pushSyntheticAction(result.label, result.ok, result.message);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Agent execution failed";
        console.error("[Copilot] agent pipeline error:", err);
        pushSyntheticAction("Error", false, message);
      } finally {
        setAgentRunning(false);
      }
    },
    [router, execute, clearActivities, pushSyntheticAction]
  );

  // ── Input router ─────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    const text = input.trim();
    if (!text || anythingRunning) return;

    setInput("");
    setOpen(true);

    // /help — local-only help text, no LLM call
    if (HELP_PREFIX.test(text)) {
      setView("chat");
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: HELP_TEXT },
      ]);
      return;
    }

    // /agent <task> — agent pipeline
    if (AGENT_PREFIX.test(text)) {
      const stripped = text.replace(AGENT_PREFIX, "").trim();
      if (!stripped) {
        setView("chat");
        setChatMessages((prev) => [
          ...prev,
          { role: "user", content: text },
          { role: "assistant", content: 'Empty agent command. Try: "/agent take me to login".' },
        ]);
        return;
      }
      await runAgent(stripped);
      return;
    }

    // Plain text — chat pipeline
    await runChat(text);
  }, [input, anythingRunning, runAgent, runChat]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleStop = useCallback(() => {
    chatAbortRef.current?.abort();
    setChatLoading(false);
    setStreamingReply(null);
    if (isPageAgentBusy) stop();
  }, [isPageAgentBusy, stop]);

  // ── FAB ──────────────────────────────────────────────────────────────────

  if (!open) {
    return (
      <>
        <AgentConfirmDialog />
        <button
          onClick={() => {
            setOpen(true);
            setTimeout(() => inputRef.current?.focus(), 150);
          }}
          className="fixed bottom-6 right-6 z-[999] flex items-center gap-2 rounded-2xl bg-brand-blue-600 hover:bg-brand-blue-500 text-white px-4 py-3 shadow-2xl shadow-brand-blue-900/50 border border-brand-blue-400/30 transition-all duration-200 hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-400"
          aria-label="Open AI Copilot"
        >
          <Bot className="size-5" />
          <span className="text-sm font-semibold hidden sm:inline">AI Copilot</span>
          <span className={`size-2 rounded-full ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`} />
        </button>
      </>
    );
  }

  // ── Panel ────────────────────────────────────────────────────────────────

  // In agent mode prefer real page-agent activities once they start arriving,
  // otherwise show synthetic ones (instant NAV / UI / UNKNOWN feedback).
  const agentFeed: AgentActivity[] = activities.length > 0 ? activities : syntheticActivities;

  return (
    <>
      <AgentConfirmDialog />

      <div
        className={`
          fixed bottom-6 right-6 z-[999] flex flex-col
          ${expanded ? "w-[440px] h-[600px]" : "w-[380px] h-[460px]"}
          rounded-2xl border border-white/10 bg-gray-950/98 backdrop-blur-xl
          shadow-2xl shadow-black/60
          transition-all duration-300 ease-in-out
        `}
        role="complementary"
        aria-label="Trady AI Copilot"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.07] shrink-0">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Bot className="size-4 text-brand-blue-400 shrink-0" />
            <span className="text-sm font-semibold text-white truncate">AI Copilot</span>
            <div className="flex items-center gap-1.5 ml-1">
              <span className={`size-1.5 rounded-full ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`} />
              <span className="text-[10px] text-slate-500">{statusCfg.label}</span>
            </div>
            {/* Mode chip */}
            <span
              className={`ml-2 px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wide ${
                view === "agent"
                  ? "bg-amber-900/30 text-amber-300 border border-amber-700/40"
                  : "bg-brand-blue-900/30 text-brand-blue-300 border border-brand-blue-700/40"
              }`}
            >
              {view === "agent" ? "Agent" : "Chat"}
            </span>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => setExpanded((v) => !v)}
              className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-white transition-colors focus:outline-none"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? <ChevronDown className="size-3.5" /> : <ChevronUp className="size-3.5" />}
            </button>
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-white transition-colors focus:outline-none"
              aria-label="Close copilot"
            >
              <X className="size-3.5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-col flex-1 min-h-0 px-3 pt-3 pb-0 gap-3 overflow-hidden">
          {/* Body — chat bubbles or agent log */}
          <div className="flex-1 min-h-0 overflow-y-auto pr-0.5 scrollbar-thin scrollbar-thumb-white/10">
            {view === "chat" ? (
              <ChatMessageList messages={chatMessages} streaming={streamingReply} />
            ) : (
              <AgentActivityFeed activities={agentFeed} />
            )}
            {chatError && view === "chat" && (
              <p className="mt-2 text-[10px] text-red-400">⚠ {chatError}</p>
            )}
          </div>
        </div>

        {/* Input */}
        <div className="px-3 pb-3 pt-2 shrink-0 border-t border-white/[0.05] mt-2">
          <div className="flex items-center gap-2 rounded-xl border border-white/[0.10] bg-white/[0.04] px-3 py-2 focus-within:border-brand-blue-500/50 transition-colors">
            <TerminalSquare className="size-3.5 text-slate-600 shrink-0" />
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder='Chat freely, or "/agent take me to login"'
              disabled={anythingRunning}
              className="flex-1 bg-transparent text-sm text-white placeholder:text-slate-600 focus:outline-none disabled:opacity-50 min-w-0"
              aria-label="AI copilot command"
            />
            {anythingRunning ? (
              <button
                onClick={handleStop}
                className="shrink-0 p-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-red-500"
                aria-label="Stop"
              >
                <Square className="size-3.5" />
              </button>
            ) : (
              <button
                onClick={() => void handleSubmit()}
                disabled={!input.trim()}
                className="shrink-0 p-1 rounded-lg bg-brand-blue-600/80 hover:bg-brand-blue-500 text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-blue-400"
                aria-label="Send"
              >
                <Send className="size-3.5" />
              </button>
            )}
          </div>
          <p className="mt-1.5 text-[10px] text-slate-700 text-center flex items-center justify-center gap-1">
            <CornerDownLeft className="size-2.5" />
            <span>Chat: LLaMA 3.2 · Agent: Qwen 2.5 (intent) → action</span>
          </p>
        </div>
      </div>
    </>
  );
}
