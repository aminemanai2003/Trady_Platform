"use client";

/**
 * use-page-agent.ts
 * React hook that exposes PageAgent state and controls to UI components.
 * Handles: execute, stop, activity stream, confirm dialog, status.
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useContext,
  createContext,
} from "react";
import type { AgentActivity, ExecutionResult, PageAgentCore } from "@page-agent/core";
import { getAgentController, disposeAgentController } from "@/lib/page-agent/agent-controller";
import { registerConfirmResolver } from "@/lib/page-agent/guardrail-middleware";

// ── Types ───────────────────────────────────────────────────────────────────

export type AgentStatus = "idle" | "running" | "completed" | "error";

export interface PendingConfirmation {
  tool: string;
  input: unknown;
  resolve: (approved: boolean) => void;
}

export interface PageAgentState {
  status: AgentStatus;
  activities: AgentActivity[];
  lastResult: ExecutionResult | null;
  pendingConfirmation: PendingConfirmation | null;
  execute: (task: string) => Promise<void>;
  stop: () => void;
  clearActivities: () => void;
  approveConfirmation: () => void;
  rejectConfirmation: () => void;
}

// ── Context ─────────────────────────────────────────────────────────────────

export const PageAgentContext = createContext<PageAgentState | null>(null);

export function usePageAgent(): PageAgentState {
  const ctx = useContext(PageAgentContext);
  if (!ctx) {
    throw new Error("usePageAgent must be used inside <PageAgentProvider>");
  }
  return ctx;
}

// ── Core hook implementation ────────────────────────────────────────────────

export function usePageAgentCore(): PageAgentState {
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [pendingConfirmation, setPendingConfirmation] =
    useState<PendingConfirmation | null>(null);

  // null until the async init resolves
  const agentRef = useRef<PageAgentCore | null>(null);

  // ── Async init + event wiring (browser-only) ─────────────────────────────
  useEffect(() => {
    let cancelled = false;
    let cleanupFn: (() => void) | null = null;

    getAgentController()
      .then((agent) => {
        if (cancelled) return;
        agentRef.current = agent;

        const handleStatusChange = () => {
          setStatus(agent.status as AgentStatus);
        };

        const handleActivity = (e: Event) => {
          const activity = (e as CustomEvent<AgentActivity>).detail;
          setActivities((prev) => [...prev.slice(-49), activity]); // keep last 50
        };

        agent.addEventListener("statuschange", handleStatusChange);
        agent.addEventListener("activity", handleActivity);

        cleanupFn = () => {
          agent.removeEventListener("statuschange", handleStatusChange);
          agent.removeEventListener("activity", handleActivity);
        };
      })
      .catch((err) => console.error("[PageAgent] init error:", err));

    return () => {
      cancelled = true;
      cleanupFn?.();
    };
  }, []);

  // ── Wire up confirmation dialog via DOM event ─────────────────────────────
  useEffect(() => {
    const handleConfirmRequired = (e: Event) => {
      const { tool, input } = (
        e as CustomEvent<{ tool: string; input: unknown }>
      ).detail;

      setPendingConfirmation({
        tool,
        input,
        resolve: (approved: boolean) => {
          registerConfirmResolver(null);
          setPendingConfirmation(null);
          // Relay approval back to guardrail
          window.dispatchEvent(
            new CustomEvent("page-agent:confirm-response", {
              detail: { approved },
            })
          );
        },
      });

      // Register a resolver callback for the guardrail middleware
      registerConfirmResolver((approved: boolean) => {
        setPendingConfirmation(null);
        return approved;
      });
    };

    window.addEventListener("page-agent:confirm-required", handleConfirmRequired);
    return () => {
      window.removeEventListener(
        "page-agent:confirm-required",
        handleConfirmRequired
      );
    };
  }, []);

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      disposeAgentController();
    };
  }, []);

  // ── Public API ────────────────────────────────────────────────────────────

  const execute = useCallback(async (task: string) => {
    const agent = agentRef.current;
    if (!agent) {
      console.warn("[PageAgent] agent not initialised yet");
      return;
    }
    setActivities([]);
    setLastResult(null);
    setStatus("running");
    try {
      const result = await agent.execute(task);
      setLastResult(result);
      setStatus(result.success ? "completed" : "error");
    } catch (err) {
      console.error("[PageAgent] execute error:", err);
      setStatus("error");
    }
  }, []);

  const stop = useCallback(() => {
    agentRef.current?.stop();
  }, []);

  const clearActivities = useCallback(() => {
    setActivities([]);
  }, []);

  const approveConfirmation = useCallback(() => {
    pendingConfirmation?.resolve(true);
  }, [pendingConfirmation]);

  const rejectConfirmation = useCallback(() => {
    pendingConfirmation?.resolve(false);
  }, [pendingConfirmation]);

  return {
    status,
    activities,
    lastResult,
    pendingConfirmation,
    execute,
    stop,
    clearActivities,
    approveConfirmation,
    rejectConfirmation,
  };
}
