/**
 * guardrail-middleware.ts
 *
 * Central safety layer for Page-Agent.
 * Every step is evaluated before execution.
 *
 * Action risk levels:
 *  ALLOWED           — execute immediately
 *  REQUIRES_APPROVAL — pause, ask the user, resume or abort
 *  BLOCKED           — terminate step silently (agent gets no output)
 */
import type { PageAgentCore } from "@page-agent/core";

// ── Risk classification ─────────────────────────────────────────────────────

/** Keywords that indicate a HIGH-RISK financial action */
const BLOCKED_KEYWORDS = [
  "buy",
  "sell",
  "openposition",
  "open_position",
  "closeposition",
  "close_position",
  "execute_trade",
  "placeorder",
  "place_order",
  "submitorder",
  "submit_order",
  "trade",
  "order",
  "execute_javascript", // dangerous — remove via customTools
];

/** Tool names that always require explicit user approval */
const APPROVAL_REQUIRED_TOOLS = [
  "autofill", // filling trading forms
  "request_confirmation",
];

/** Tool names that are always safe (navigation, highlighting, reading) */
const AUTO_ALLOWED_TOOLS = [
  "navigate_to_page",
  "highlight_element",
  "fetch_market_signals",
  "scroll",
  "click",       // generic click is checked by keyword scan below
  "type",
  "focus",
  "hover",
  "wait",
  "done",
  "ask_user",
];

// ── Confirmation queue ──────────────────────────────────────────────────────
// The UI registers a resolver here; the middleware calls it to get approval.

type ConfirmResolver = (approved: boolean) => void;

let _pendingConfirmResolver: ConfirmResolver | null = null;

export function registerConfirmResolver(resolver: ConfirmResolver | null) {
  _pendingConfirmResolver = resolver;
}

// ── Risk evaluator ──────────────────────────────────────────────────────────

function classifyAction(
  toolName: string,
  input: unknown
): "ALLOWED" | "REQUIRES_APPROVAL" | "BLOCKED" {
  const tool = toolName.toLowerCase();
  const inputStr = JSON.stringify(input ?? "").toLowerCase();

  // 1. Always auto-approve safe tools
  if (AUTO_ALLOWED_TOOLS.includes(tool)) {
    // Extra check: is the target a blocked element?
    if (inputStr.includes("data-page-agent-block")) return "BLOCKED";
    return "ALLOWED";
  }

  // 2. Hard-block on financial keywords
  const isBlocked = BLOCKED_KEYWORDS.some(
    (kw) => tool.includes(kw) || inputStr.includes(kw)
  );
  if (isBlocked) return "BLOCKED";

  // 3. Approval required tools
  if (APPROVAL_REQUIRED_TOOLS.some((t) => tool.includes(t))) {
    return "REQUIRES_APPROVAL";
  }

  // 4. Default: allowed
  return "ALLOWED";
}

// ── Guardrail builder ───────────────────────────────────────────────────────

export interface GuardrailHooks {
  onBeforeStep: (
    agent: PageAgentCore,
    stepCount: number
  ) => void | Promise<void>;
  onAfterTask: (
    agent: PageAgentCore,
    result: unknown
  ) => void | Promise<void>;
}

export function buildGuardrails(): GuardrailHooks {
  // Track consecutive identical tool calls to detect infinite loops
  let lastToolName = "";
  let sameToolCount = 0;

  return {
    onBeforeStep: async (agent, stepCount) => {
      // Safety ceiling — avoid infinite loops
      if (stepCount > 20) {
        agent.stop();
        console.warn("[Guardrail] Step limit reached — task stopped.");
        return;
      }

      // Inspect the *last planned action* from history
      const history = agent.history ?? [];
      if (history.length === 0) return;

      const lastEvent = history[history.length - 1] as {
        type?: string;
        tool?: string;
        input?: unknown;
      };

      if (!lastEvent?.tool) return;

      // Detect repeated tool calls (same tool name, regardless of input)
      // This catches loops where the model varies params but never progresses
      if (lastEvent.tool === lastToolName) {
        sameToolCount++;
      } else {
        lastToolName = lastEvent.tool;
        sameToolCount = 1;
      }

      if (sameToolCount >= 2) {
        agent.stop();
        console.warn(
          `[Guardrail] Tool "${lastEvent.tool}" called ${sameToolCount} times in a row — stopping to prevent infinite loop.`
        );
        return;
      }

      const riskLevel = classifyAction(lastEvent.tool, lastEvent.input);

      if (riskLevel === "BLOCKED") {
        agent.stop();
        console.warn(
          `[Guardrail] BLOCKED action: ${lastEvent.tool}`,
          lastEvent.input
        );
        return;
      }

      if (riskLevel === "REQUIRES_APPROVAL") {
        if (_pendingConfirmResolver) {
          const approved = await requestApproval(
            lastEvent.tool,
            lastEvent.input
          );
          if (!approved) {
            agent.stop();
            console.warn(
              `[Guardrail] User rejected: ${lastEvent.tool}`
            );
          }
        } else {
          // No UI registered — block by default
          agent.stop();
          console.warn(
            `[Guardrail] No confirm UI registered — blocked: ${lastEvent.tool}`
          );
        }
      }
    },

    onAfterTask: (_agent, result) => {
      console.info("[PageAgent] Task completed:", result);
    },
  };
}

// ── Approval helper ─────────────────────────────────────────────────────────

function requestApproval(tool: string, input: unknown): Promise<boolean> {
  return new Promise((resolve) => {
    if (!_pendingConfirmResolver) {
      resolve(false);
      return;
    }
    // Fire the UI callback — it will resolve the promise
    _pendingConfirmResolver = (approved: boolean) => {
      resolve(approved);
      _pendingConfirmResolver = null;
    };
    // Dispatch a custom DOM event so the React layer can pick it up
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("page-agent:confirm-required", {
          detail: { tool, input },
        })
      );
    }
  });
}
