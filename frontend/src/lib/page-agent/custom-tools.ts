/**
 * custom-tools.ts
 * Extends Page-Agent with Trady-specific tools and removes dangerous built-ins.
 *
 * `page-agent` accesses `window` at module evaluation time — `tool` is
 * imported dynamically inside buildCustomTools() to prevent SSR crashes.
 */
import { z } from "zod/v4";
import type { PageAgentTool } from "@page-agent/core";
import { resolveElement } from "./element-registry";

// ── Route whitelist for navigation tool ────────────────────────────────────
const ALLOWED_ROUTES: Record<string, string> = {
  dashboard: "/dashboard",
  trading: "/trading",
  agents: "/agents",
  "signal lab": "/agents",
  analytics: "/analytics",
  reports: "/reports",
  "strategy tutor": "/strategy-tutor",
  tutor: "/strategy-tutor",
  backtesting: "/backtesting",
  monitoring: "/monitoring",
  settings: "/settings",
  login: "/login",
  signin: "/login",
  "sign in": "/login",
  register: "/register",
  signup: "/register",
  "sign up": "/register",
  home: "/",
  landing: "/",
};

// ── Async builder (must be called from a browser context) ──────────────────

export async function buildCustomTools(): Promise<Record<string, PageAgentTool | null>> {
  const { tool } = await import("page-agent");

  const navigate_to_page = tool({
  description:
    "Navigate to a named Trady page. Allowed targets: dashboard, trading, agents, analytics, reports, strategy-tutor, backtesting, monitoring, settings, login, register, home.",
  inputSchema: z.object({
    page: z
      .string()
      .describe(
        "Target page name (e.g. 'agents', 'analytics', 'strategy tutor')"
      ),
  }),
  execute: async ({ page }) => {
    const route = ALLOWED_ROUTES[page.toLowerCase().trim()];
    if (!route) {
      return `Unknown page: "${page}". Available: ${Object.keys(ALLOWED_ROUTES).join(", ")}`;
    }
    if (typeof window !== "undefined") {
      window.location.href = route;
    }
    return `Navigated to ${route}`;
  },
});

const highlight_element = tool({
  description:
    "Temporarily highlight a DOM element to draw the user's attention. Uses a CSS selector.",
  inputSchema: z.object({
    selector: z.string().describe("CSS selector of the element to highlight"),
    durationMs: z
      .number()
      .min(500)
      .max(5000)
      .default(2500)
      .describe("How long to show the highlight (ms)"),
    label: z.string().optional().describe("Optional tooltip label to show"),
  }),
  execute: async ({ selector, durationMs, label }) => {
    if (typeof document === "undefined") return "DOM not available";

    let el: Element | null = null;

    // The model sometimes passes page-agent's indexed element notation
    // e.g. "[6]<button aria-label=Expand />" instead of a CSS selector.
    // Try to resolve it to the actual element.
    const indexedMatch = selector.match(/^\[(\d+)\]/);
    if (indexedMatch) {
      // Extract tag and attributes from the notation
      const tagMatch = selector.match(/^\[\d+\]<(\w+)([^>]*)\/?>$/);
      if (tagMatch) {
        const tag = tagMatch[1];
        const attrStr = tagMatch[2].trim();
        // Try to build a valid CSS selector from tag + attributes
        const ariaMatch = attrStr.match(/aria-label=([^\s/>]+)/);
        if (ariaMatch) {
          try {
            el = document.querySelector(`${tag}[aria-label="${ariaMatch[1]}"]`);
          } catch { /* ignore */ }
        }
        if (!el) {
          // Fallback: get all elements of that tag and try the index
          const allOfTag = document.querySelectorAll(tag);
          const idx = parseInt(indexedMatch[1], 10);
          if (idx < allOfTag.length) el = allOfTag[idx];
        }
      }
      // Last resort: use the numeric index across all interactive elements
      if (!el) {
        const interactive = document.querySelectorAll(
          "a, button, input, select, textarea, [role='button'], [tabindex]"
        );
        const idx = parseInt(indexedMatch[1], 10);
        if (idx < interactive.length) el = interactive[idx];
      }
    } else {
      // Standard CSS selector path
      try {
        el = document.querySelector(selector);
      } catch {
        return `Invalid CSS selector: ${selector}`;
      }
    }

    if (!el) return `Element not found: ${selector}`;

    // Safety: never highlight blocked elements
    if (el.hasAttribute("data-page-agent-block")) {
      return "Cannot highlight a blocked element.";
    }

    const overlay = document.createElement("div");
    overlay.setAttribute("data-page-agent-highlight", "true");
    overlay.style.cssText = `
      position: fixed;
      z-index: 9999;
      pointer-events: none;
      border: 2px solid #3b82f6;
      border-radius: 6px;
      box-shadow: 0 0 0 4px rgba(59,130,246,0.25);
      transition: opacity 0.3s ease;
      background: rgba(59,130,246,0.08);
    `;

    const rect = el.getBoundingClientRect();
    overlay.style.top = `${rect.top - 4}px`;
    overlay.style.left = `${rect.left - 4}px`;
    overlay.style.width = `${rect.width + 8}px`;
    overlay.style.height = `${rect.height + 8}px`;

    if (label) {
      const tooltip = document.createElement("div");
      tooltip.textContent = label;
      tooltip.style.cssText = `
        position: absolute;
        top: -28px;
        left: 0;
        background: #1e40af;
        color: white;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
        white-space: nowrap;
        font-family: var(--font-manrope, sans-serif);
      `;
      overlay.appendChild(tooltip);
    }

    document.body.appendChild(overlay);
    el.scrollIntoView({ behavior: "smooth", block: "center" });

    await new Promise((r) => setTimeout(r, durationMs));
    overlay.style.opacity = "0";
    await new Promise((r) => setTimeout(r, 300));
    overlay.remove();

    return `Highlighted: ${selector}`;
  },
});

const fetch_market_signals = tool({
  description:
    "Fetch the latest trading signals from Trady's backend for a given currency pair. Returns signal direction, confidence, and risk level.",
  inputSchema: z.object({
    pair: z
      .enum(["EURUSD", "USDJPY", "USDCHF", "GBPUSD"])
      .describe("Currency pair"),
  }),
  execute: async ({ pair }) => {
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
      const res = await fetch(`${apiBase}/signals/latest/?pair=${pair}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        signal?: string;
        confidence?: number;
        risk_level?: string;
        reasoning?: string;
      };
      return JSON.stringify({
        pair,
        signal: data.signal ?? "N/A",
        confidence: data.confidence ?? null,
        risk_level: data.risk_level ?? "N/A",
        reasoning: data.reasoning ?? "",
      });
    } catch (e) {
      return `Could not fetch signals for ${pair}: ${e instanceof Error ? e.message : String(e)}`;
    }
  },
});

const request_confirmation = tool({
  description:
    "Ask the user to explicitly confirm a sensitive action before proceeding. Always use this before autofilling trading parameters.",
  inputSchema: z.object({
    action_summary: z
      .string()
      .describe("Human-readable description of the action requiring approval"),
  }),
  execute: async ({ action_summary }) => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("page-agent:confirm-required", {
          detail: { tool: "request_confirmation", input: { action_summary } },
        })
      );
    }
    // The actual approval flow is handled by the guardrail resolver —
    // this tool just signals the intent
    return `Confirmation requested: ${action_summary}`;
  },
});

const submit_login_form = tool({
  description:
    "Submit the login form on the login page — clicks the Sign In button. Use this when the user says 'click sign in', 'sign in', 'log in', 'submit login', etc. while on the /login page.",
  inputSchema: z.object({}),
  execute: async () => {
    if (typeof document === "undefined") return "DOM not available";
    const btn = document.querySelector<HTMLElement>("#sign-in-btn") ??
                document.querySelector<HTMLElement>("button[type='submit']");
    if (!btn) return "Sign in button not found. Make sure you are on the login page.";
    btn.scrollIntoView({ behavior: "smooth", block: "center" });
    btn.focus();
    btn.click();
    return "Clicked Sign in button.";
  },
});

const click_element = tool({
  description:
    "Click a named UI element in the Trady app by its natural-language name. Examples: 'generate signal', 'export csv', 'logout', 'analytics performance tab', 'save settings'. Resolves the element through the central registry.",
  inputSchema: z.object({
    element_name: z
      .string()
      .describe(
        "Natural-language name of the element to click, e.g. 'generate signal', 'refresh all', 'logout', 'performance tab'"
      ),
  }),
  execute: async ({ element_name }) => {
    if (typeof document === "undefined") return "DOM not available";

    const entry = resolveElement(element_name);
    if (!entry) {
      return `Unknown element: "${element_name}". Try saying the element's label as shown on screen.`;
    }
    if (entry.blocked) {
      return `"${entry.label}" is blocked from AI automation for safety. Please interact with it manually.`;
    }

    let el: HTMLElement | null = null;
    for (const selector of entry.selectors) {
      try {
        const found = document.querySelector<HTMLElement>(selector);
        if (found) { el = found; break; }
      } catch { /* bad selector — skip */ }
    }

    if (!el) {
      const suggestion = entry.page ? ` Make sure you are on the ${entry.page} page.` : "";
      return `Element "${entry.label}" not found in the DOM.${suggestion}`;
    }

    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.focus();
    // Dispatch synthetic mouse events for React synthetic event handlers
    el.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    el.dispatchEvent(new MouseEvent("mouseup",   { bubbles: true, cancelable: true }));
    el.click();

    return `Clicked: ${entry.label}`;
  },
});

  // ── Assemble and return ──────────────────────────────────────────────────
  return {
    navigate_to_page,
    highlight_element,
    fetch_market_signals,
    request_confirmation,
    submit_login_form,
    click_element,

    // Remove dangerous built-in tools
    execute_javascript: null,
  };
}
