/**
 * execution-engine.ts
 * Frontend handlers for the validated Action union returned by /api/intent.
 *
 * The router instance and page-agent.execute() callback are injected at call
 * time so this module stays free of React hooks and can be unit-tested.
 *
 * Responsibilities (one per Action variant):
 *   NAVIGATION     → router.push(target)
 *   UI_ACTION      → resolve via element-registry, click / highlight / focus / submit
 *   AGENT_TASK     → defer to page-agent (multi-step LLM workflow)
 *   UNKNOWN_ACTION → return a safe error result; never throw, never execute
 */

import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { resolveElement } from "./element-registry";

// ── Action type (mirrors the server-side validator) ────────────────────────

export type Action =
  | { type: "NAVIGATION"; target: string }
  | { type: "UI_ACTION"; action: "click" | "highlight" | "focus" | "submit"; target: string }
  | { type: "AGENT_TASK"; task: string; input: string }
  | { type: "UNKNOWN_ACTION"; reason: string };

export interface ExecutionResult {
  ok: boolean;
  message: string;
  /** Stable label suitable for the activity log */
  label: string;
}

export interface ExecutionContext {
  router: AppRouterInstance;
  /** Defer multi-step workflows to the page-agent LLM loop */
  runPageAgent: (task: string) => Promise<void>;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function findElement(target: string): HTMLElement | null {
  // First: registry lookup (handles natural-language labels)
  const entry = resolveElement(target);
  if (entry) {
    for (const sel of entry.selectors) {
      try {
        const el = document.querySelector<HTMLElement>(sel);
        if (el) return el;
      } catch {
        /* invalid selector — skip */
      }
    }
  }
  // Fallback: treat the target itself as a CSS selector
  try {
    return document.querySelector<HTMLElement>(target);
  } catch {
    return null;
  }
}

function highlightElement(el: HTMLElement): void {
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  const previousOutline = el.style.outline;
  const previousOffset = el.style.outlineOffset;
  el.style.outline = "2px solid rgb(59 130 246)";
  el.style.outlineOffset = "2px";
  window.setTimeout(() => {
    el.style.outline = previousOutline;
    el.style.outlineOffset = previousOffset;
  }, 1800);
}

// ── Per-Action handlers ────────────────────────────────────────────────────

function handleNavigation(
  action: Extract<Action, { type: "NAVIGATION" }>,
  ctx: ExecutionContext
): ExecutionResult {
  ctx.router.push(action.target);
  return {
    ok: true,
    label: `Navigate → ${action.target}`,
    message: `Navigating to ${action.target}`,
  };
}

function handleUiAction(
  action: Extract<Action, { type: "UI_ACTION" }>
): ExecutionResult {
  const el = findElement(action.target);
  if (!el) {
    return {
      ok: false,
      label: `UI action failed`,
      message: `Element not found: "${action.target}"`,
    };
  }

  switch (action.action) {
    case "click":
      highlightElement(el);
      el.focus();
      el.click();
      return { ok: true, label: `Click → ${action.target}`, message: `Clicked "${action.target}"` };
    case "highlight":
      highlightElement(el);
      return { ok: true, label: `Highlight → ${action.target}`, message: `Highlighted "${action.target}"` };
    case "focus":
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus();
      return { ok: true, label: `Focus → ${action.target}`, message: `Focused "${action.target}"` };
    case "submit": {
      const form = el.closest("form");
      if (!form) {
        return {
          ok: false,
          label: `Submit failed`,
          message: `No <form> ancestor for "${action.target}"`,
        };
      }
      form.requestSubmit();
      return { ok: true, label: `Submit → ${action.target}`, message: `Submitted form for "${action.target}"` };
    }
  }
}

async function handleAgentTask(
  action: Extract<Action, { type: "AGENT_TASK" }>,
  ctx: ExecutionContext
): Promise<ExecutionResult> {
  await ctx.runPageAgent(action.input);
  return {
    ok: true,
    label: `Agent → ${action.task}`,
    message: `Running agent task: ${action.task}`,
  };
}

function handleUnknown(
  action: Extract<Action, { type: "UNKNOWN_ACTION" }>
): ExecutionResult {
  return {
    ok: false,
    label: "Unknown command",
    message: action.reason || "I could not understand that command.",
  };
}

// ── Public entry point ─────────────────────────────────────────────────────

export async function executeAction(
  action: Action,
  ctx: ExecutionContext
): Promise<ExecutionResult> {
  switch (action.type) {
    case "NAVIGATION":
      return handleNavigation(action, ctx);
    case "UI_ACTION":
      return handleUiAction(action);
    case "AGENT_TASK":
      return handleAgentTask(action, ctx);
    case "UNKNOWN_ACTION":
      return handleUnknown(action);
  }
}

// ── Client helper for /api/intent ──────────────────────────────────────────

export async function fetchIntent(text: string): Promise<Action> {
  try {
    const res = await fetch("/api/intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      return { type: "UNKNOWN_ACTION", reason: `Intent API ${res.status}` };
    }
    const data = (await res.json()) as { action?: Action };
    if (!data.action) {
      return { type: "UNKNOWN_ACTION", reason: "Empty intent response" };
    }
    return data.action;
  } catch (err) {
    const reason = err instanceof Error ? err.message : "network error";
    return { type: "UNKNOWN_ACTION", reason };
  }
}
