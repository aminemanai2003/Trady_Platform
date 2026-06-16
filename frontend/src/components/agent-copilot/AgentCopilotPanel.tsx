"use client";

/**
 * AgentCopilotPanel — Input router for the Trady Copilot.
 *
 * Pipelines:
 *   /agent <text>  → /api/intent → executeAction(...)
 *   <text>         → /api/chat   → streamed chat bubbles
 *
 * No regex-based intent parsing here: classification is delegated to /api/intent.
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
  Mic,
  MicOff,
} from "lucide-react";
import { usePageAgent } from "@/hooks/use-page-agent";
import { useVoiceInput, extractAgentCommand } from "@/hooks/use-voice-input";
import { AgentActivityFeed } from "./AgentActivityFeed";
import { AgentConfirmDialog } from "./AgentConfirmDialog";
import { ChatMessageList } from "./ChatMessageList";
import { fetchIntent, executeAction, type Action } from "@/lib/page-agent/execution-engine";
import { streamChat, type ChatMessage } from "@/lib/page-agent/chat-client";

// ── Mode + slash-command detection ─────────────────────────────────────────

const AGENT_PREFIX = /^\/agent(\s+|$)/i;
const HELP_PREFIX = /^\/(help|\?)\s*$/i;

const HELP_TEXT = [
  "Trady AI Copilot usage:",
  "",
  "Ask questions about Trady, navigation, trading tools, or reports.",
  "Use /agent for guided actions across the app.",
  "    Examples:",
  "      /agent take me to login",
  "      /agent open the dashboard",
  "      /agent click the signup button",
  "      /agent run a guided onboarding tour",
  "Use /help to show this message.",
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

  // Voice-input state. `voiceError` shows transient mic problems under the input.
  const [voiceError, setVoiceError] = useState<string | null>(null);

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
        tool: "copilot_action",
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

  // Accepts an optional explicit text so voice handlers can submit without
  // relying on React having committed `setInput` yet.
  const handleSubmit = useCallback(async (explicit?: string) => {
    const text = (explicit ?? input).trim();
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

  // ── Voice input ──────────────────────────────────────────────────────────
  // Wake-word "agent" → /agent pipeline. Otherwise → chat. Mirrors the same
  // routing as the text input.

  const voice = useVoiceInput({
    onInterim: (live) => {
      setVoiceError(null);
      setInput(live);
    },
    onFinal: (transcript) => {
      const text = transcript.trim();
      if (!text) return;
      const agentBody = extractAgentCommand(text);
      const finalText =
        agentBody !== null
          ? agentBody.length > 0
            ? `/agent ${agentBody}`
            : "/agent"
          : text;
      setInput(finalText);
      // Submit on the next tick so the user briefly sees the recognised text
      // before it disappears from the input — feels less abrupt than instant
      // submission, and matches what dictation in macOS / Word does.
      window.setTimeout(() => void handleSubmit(finalText), 220);
    },
    onError: (message) => {
      setVoiceError(message);
      // Auto-dismiss after a few seconds so the input UI doesn't get stuck.
      window.setTimeout(() => setVoiceError(null), 4000);
    },
  });

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
          fixed bottom-4 left-4 right-4 sm:bottom-6 sm:left-auto sm:right-6 z-[999] flex flex-col
          w-auto ${expanded ? "sm:w-[440px] sm:max-w-[calc(100vw-3rem)] h-[min(600px,calc(100dvh-2rem))]" : "sm:w-[380px] sm:max-w-[calc(100vw-3rem)] h-[min(460px,calc(100dvh-2rem))]"}
          overflow-hidden rounded-xl border border-border bg-popover/95 text-popover-foreground backdrop-blur-xl
          shadow-[0_24px_70px_rgba(15,23,42,0.22)] dark:shadow-black/60
          transition-all duration-300 ease-in-out
        `}
        role="complementary"
        aria-label="Trady AI Copilot"
        data-testid="agent-copilot-panel"
      >
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border bg-card/60 px-4 py-3 shrink-0">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-brand-blue-600 text-white">
              <Bot className="size-4" />
            </div>
            <span className="text-sm font-semibold text-foreground truncate">AI Copilot</span>
            <div className="flex items-center gap-1.5 ml-1">
              <span className={`size-1.5 rounded-full ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`} />
              <span className="text-[10px] text-muted-foreground">{statusCfg.label}</span>
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
              className="p-1.5 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus:outline-none"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? <ChevronDown className="size-3.5" /> : <ChevronUp className="size-3.5" />}
            </button>
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus:outline-none"
              aria-label="Close copilot"
            >
              <X className="size-3.5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-col flex-1 min-h-0 px-3 pt-3 pb-0 gap-3 overflow-hidden">
          {/* Body — chat bubbles or agent log */}
          <div className="flex-1 min-h-0 overflow-y-auto pr-0.5">
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
        <div className="px-3 pb-3 pt-3 shrink-0 border-t border-border bg-card/40 mt-2">
          <div className="flex items-center gap-2 rounded-lg border border-input bg-background px-3 py-2.5 shadow-sm focus-within:border-brand-blue-500 focus-within:ring-2 focus-within:ring-brand-blue-500/15 transition-colors">
            <TerminalSquare className="size-3.5 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={voice.recording ? "Listening… try \"agent take me to login\"" : 'Chat freely, or "/agent take me to login"'}
              disabled={anythingRunning}
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50 min-w-0"
              aria-label="AI copilot command"
            />
            {/* Mic button — only rendered when the browser actually supports
                SpeechRecognition. Firefox/Safari users will just see the Send
                button as before. */}
            {voice.supported && (
              <button
                onClick={voice.toggle}
                disabled={anythingRunning}
                title={voice.recording ? "Stop listening" : 'Voice input — say "agent …" to run an action'}
                aria-label={voice.recording ? "Stop listening" : "Start voice input"}
                aria-pressed={voice.recording}
                className={`shrink-0 p-1 rounded-lg transition-colors focus:outline-none focus-visible:ring-1 disabled:opacity-30 disabled:cursor-not-allowed ${
                  voice.recording
                    ? "bg-red-500/20 text-red-400 hover:bg-red-500/30 focus-visible:ring-red-500 animate-pulse"
                    : "bg-accent/50 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-brand-blue-400"
                }`}
              >
                {voice.recording ? <MicOff className="size-3.5" /> : <Mic className="size-3.5" />}
              </button>
            )}
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
          {voiceError ? (
            <p className="mt-2 text-[10px] text-red-400 text-center">⚠ {voiceError}</p>
          ) : voice.recording ? (
            <p className="mt-2 text-[10px] text-red-400 text-center flex items-center justify-center gap-1">
              <span className="size-1.5 rounded-full bg-red-500 animate-pulse" />
              Listening… tap the mic again when you're done
            </p>
          ) : (
            <p className="mt-2 text-[10px] text-muted-foreground text-center flex items-center justify-center gap-1">
              <CornerDownLeft className="size-2.5" />
              <span>Ask questions or run guided actions{voice.supported && " · tap the mic to dictate"}</span>
            </p>
          )}
        </div>
      </div>
    </>
  );
}
