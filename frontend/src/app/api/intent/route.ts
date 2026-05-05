import { NextRequest, NextResponse } from "next/server";

/**
 * /api/intent — strict structured-output endpoint.
 *
 * Input:  { text: string }   (the slash-command body, "/agent" already stripped)
 * Output: { action: Action } where Action is one of the union members below.
 *
 * Pipeline:
 *   1. Send text + system prompt + JSON schema to Ollama (Qwen 2.5 3B, temperature 0).
 *   2. Parse the model output as JSON (response_format=json_object).
 *   3. Validate against the Action schema. Anything invalid → UNKNOWN_ACTION.
 *
 * The frontend never sees raw model output — only a validated Action.
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

const INTENT_MODEL = process.env.OLLAMA_INTENT_MODEL ?? "qwen2.5:3b";

// ── Action schema (mirrors the TypeScript union the frontend executes) ─────

const ALLOWED_ROUTES = [
  "/login",
  "/register",
  "/dashboard",
  "/trading",
  "/agents",
  "/analytics",
  "/reports",
  "/tutor",
  "/backtesting",
] as const;

type AllowedRoute = (typeof ALLOWED_ROUTES)[number];

const ALLOWED_UI_ACTIONS = ["click", "highlight", "focus", "submit"] as const;
type AllowedUiAction = (typeof ALLOWED_UI_ACTIONS)[number];

export type Action =
  | { type: "NAVIGATION"; target: AllowedRoute }
  | { type: "UI_ACTION"; action: AllowedUiAction; target: string }
  | { type: "AGENT_TASK"; task: string; input: string }
  | { type: "UNKNOWN_ACTION"; reason: string };

// ── System prompt — strict, JSON-only ──────────────────────────────────────

const SYSTEM_PROMPT = `You are an intent classifier for the Trady forex platform. You output JSON ONLY.

Your job: read a single user command and emit one Action object that the frontend will execute.

OUTPUT FORMAT (return exactly one of these JSON shapes, nothing else):
  { "type": "NAVIGATION", "target": "/<route>" }
  { "type": "UI_ACTION", "action": "<click|highlight|focus|submit>", "target": "<element label or selector>" }
  { "type": "AGENT_TASK", "task": "<short label>", "input": "<the original user command>" }
  { "type": "UNKNOWN_ACTION", "reason": "<short reason>" }

ALLOWED ROUTES (NAVIGATION.target must be exactly one of these):
  /login, /register, /dashboard, /trading, /agents, /analytics, /reports, /tutor, /backtesting

ROUTING RULES (apply in order):
  1. If the user asks to go to / open / navigate to / take them to a known page → NAVIGATION.
     - "login" / "sign in" → /login
     - "register" / "sign up" → /register
     - "dashboard" / "home" → /dashboard
     - "trading" / "chart" → /trading
     - "agents" / "signals" / "signal lab" → /agents
     - "analytics" / "performance" → /analytics
     - "reports" → /reports
     - "tutor" / "strategy tutor" → /tutor
     - "backtesting" / "backtest" → /backtesting
  2. If the user asks to click / press / submit / highlight a specific UI element on the current page → UI_ACTION.
     - "click the signup button" → { "type": "UI_ACTION", "action": "click", "target": "signup button" }
  3. If the user describes a multi-step workflow (tour, fetch a signal, run analysis, anything that needs more than one navigation/click) → AGENT_TASK.
     - input MUST be a verbatim copy of the user command.
     - task MUST be a short imperative label (≤6 words).
  4. Anything else, off-topic, or ambiguous → UNKNOWN_ACTION with a brief reason.

HARD RULES:
  - Output JSON only. No prose. No code fences. No comments.
  - Never invent routes that are not in the ALLOWED ROUTES list. If the user asks for an unknown page, return UNKNOWN_ACTION.
  - Never guess. If you cannot confidently classify, return UNKNOWN_ACTION.
  - Do not output any field not listed in the schema.`;

// ── Validators ─────────────────────────────────────────────────────────────

function isAllowedRoute(v: unknown): v is AllowedRoute {
  return typeof v === "string" && (ALLOWED_ROUTES as readonly string[]).includes(v);
}

function isAllowedUiAction(v: unknown): v is AllowedUiAction {
  return typeof v === "string" && (ALLOWED_UI_ACTIONS as readonly string[]).includes(v);
}

function validateAction(raw: unknown): Action {
  if (!raw || typeof raw !== "object") {
    return { type: "UNKNOWN_ACTION", reason: "Parser returned non-object" };
  }
  const obj = raw as Record<string, unknown>;

  switch (obj.type) {
    case "NAVIGATION": {
      if (!isAllowedRoute(obj.target)) {
        return { type: "UNKNOWN_ACTION", reason: `Route not allowed: ${String(obj.target)}` };
      }
      return { type: "NAVIGATION", target: obj.target };
    }
    case "UI_ACTION": {
      if (!isAllowedUiAction(obj.action)) {
        return { type: "UNKNOWN_ACTION", reason: `UI action not allowed: ${String(obj.action)}` };
      }
      if (typeof obj.target !== "string" || obj.target.trim().length === 0) {
        return { type: "UNKNOWN_ACTION", reason: "UI_ACTION.target missing" };
      }
      return { type: "UI_ACTION", action: obj.action, target: obj.target.trim() };
    }
    case "AGENT_TASK": {
      const task = typeof obj.task === "string" ? obj.task.trim() : "";
      const input = typeof obj.input === "string" ? obj.input.trim() : "";
      if (!task || !input) {
        return { type: "UNKNOWN_ACTION", reason: "AGENT_TASK requires task and input" };
      }
      return { type: "AGENT_TASK", task, input };
    }
    case "UNKNOWN_ACTION": {
      const reason = typeof obj.reason === "string" ? obj.reason : "Unspecified";
      return { type: "UNKNOWN_ACTION", reason };
    }
    default:
      return { type: "UNKNOWN_ACTION", reason: `Unknown action type: ${String(obj.type)}` };
  }
}

// ── JSON extraction (model may emit prefix/suffix garbage even with json_object) ─

function extractJson(raw: string): unknown {
  const trimmed = raw.trim();
  // Fast path
  try {
    return JSON.parse(trimmed);
  } catch {
    /* fall through */
  }
  // Strip code fences
  const fenced = trimmed.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "");
  try {
    return JSON.parse(fenced);
  } catch {
    /* fall through */
  }
  // Last resort: find first {...} block
  const match = trimmed.match(/\{[\s\S]*\}/);
  if (match) {
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
  return null;
}

// ── Route handler ──────────────────────────────────────────────────────────

interface IntentRequestBody {
  text?: string;
}

export async function POST(req: NextRequest) {
  let body: IntentRequestBody;
  try {
    body = (await req.json()) as IntentRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const text = typeof body.text === "string" ? body.text.trim() : "";
  if (!text) {
    return NextResponse.json({ error: "text required" }, { status: 400 });
  }

  const upstream = await fetch(`${OLLAMA_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: INTENT_MODEL,
      stream: false,
      temperature: 0,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: text },
      ],
    }),
  }).catch((err: unknown) => {
    console.error("[/api/intent] upstream fetch failed:", err);
    return null;
  });

  if (!upstream || !upstream.ok) {
    const status = upstream?.status ?? 502;
    const reason = upstream ? await upstream.text().catch(() => "") : "unreachable";
    console.error(`[/api/intent] upstream error ${status}: ${reason}`);
    const fallback: Action = {
      type: "UNKNOWN_ACTION",
      reason: "Intent parser unavailable",
    };
    return NextResponse.json({ action: fallback }, { status: 200 });
  }

  let upstreamJson: unknown;
  try {
    upstreamJson = await upstream.json();
  } catch {
    const fallback: Action = { type: "UNKNOWN_ACTION", reason: "Parser returned non-JSON" };
    return NextResponse.json({ action: fallback }, { status: 200 });
  }

  const content = (upstreamJson as { choices?: Array<{ message?: { content?: string } }> })
    ?.choices?.[0]?.message?.content;

  if (typeof content !== "string" || content.length === 0) {
    const fallback: Action = { type: "UNKNOWN_ACTION", reason: "Empty parser output" };
    return NextResponse.json({ action: fallback }, { status: 200 });
  }

  const parsed = extractJson(content);
  const action = validateAction(parsed);

  console.log(
    `[/api/intent] in="${text.slice(0, 80)}" → ${action.type}${
      "target" in action ? ` (${(action as { target: string }).target})` : ""
    }`
  );

  return NextResponse.json({ action }, { status: 200 });
}
