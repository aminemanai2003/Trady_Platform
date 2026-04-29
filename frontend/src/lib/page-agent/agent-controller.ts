/**
 * agent-controller.ts
 * Singleton wrapper around PageAgentCore.
 * Initialised lazily on first call to getAgentController().
 * Connects to Ollama via the /api/llm-proxy Next.js route.
 *
 * @page-agent/page-controller accesses `window` at module level, so all
 * page-agent imports are dynamic to prevent SSR evaluation errors.
 */
import type { PageAgentCore } from "@page-agent/core";

import { buildInstructions } from "./instructions";
import { buildCustomTools } from "./custom-tools";
import { buildGuardrails } from "./guardrail-middleware";

let _instance: PageAgentCore | null = null;

export async function getAgentController(): Promise<PageAgentCore> {
  if (typeof window === "undefined") {
    throw new Error("[PageAgent] client-only — do not call on the server");
  }
  if (_instance) return _instance;

  const { PageAgentCore } = await import("@page-agent/core");
  const { PageController } = await import("@page-agent/page-controller");

  const pageController = new PageController({ enableMask: true });

  const guardrails = buildGuardrails();

  _instance = new PageAgentCore({
    pageController,

    // ── LLM (Ollama via internal proxy) ─────────────────────────────────────
    baseURL: "/api/llm-proxy",
    model: "llama3.2:3b",
    // llama3.2:3b reliably calls AgentOutput when tool_choice is named explicitly.
    // disableNamedToolChoice must be FALSE — with "required" (the fallback) the model ignores tools.
    disableNamedToolChoice: false,
    // No apiKey — Ollama is password-less by default
    // customFetch sends session cookie for authentication on the proxy route
    customFetch: ((url: RequestInfo | URL, init?: RequestInit) =>
      fetch(url, { ...init, credentials: "include" })) as typeof globalThis.fetch,

    temperature: 0.1,
    maxRetries: 2,

    // ── Agent behaviour ──────────────────────────────────────────────────────
    language: "en-US",
    maxSteps: 25,

    instructions: buildInstructions(),
    customTools: await buildCustomTools(),

    // ── Guardrail lifecycle hooks ────────────────────────────────────────────
    onBeforeStep: guardrails.onBeforeStep,
    onAfterTask: guardrails.onAfterTask,
  });

  return _instance;
}

/**
 * Disposes and nullifies the singleton.
 * Call this on logout to avoid cross-session contamination.
 */
export function disposeAgentController(): void {
  if (_instance) {
    _instance.dispose();
    _instance = null;
  }
}
