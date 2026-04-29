import { NextRequest, NextResponse } from "next/server";

/**
 * Catch-all proxy for page-agent LLM requests.
 * page-agent calls baseURL + "/chat/completions", "/models", etc.
 * This route handles /api/llm-proxy/* → Ollama.
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

const ALLOWED_SEGMENTS = ["chat/completions", "models", "completions"];

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToOllama(req, path);
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToOllama(req, path);
}

/**
 * Try to infer a valid page-agent action from the model's malformed response.
 * Small models often output action as {"type":"object","params":{"tool":"inspect"}}
 * or similar hallucinated structures.
 */
function inferActionFromContext(args: Record<string, unknown>): Record<string, unknown> {
  // Check if next_goal or memory hints at the intended action
  const hints = [
    args.next_goal,
    args.memory,
    args.evaluation_previous_goal,
    JSON.stringify(args.action),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (hints.includes("click") || hints.includes("button") || hints.includes("press")) {
    // Try to extract an index number from the hints
    const indexMatch = hints.match(/\[?(\d+)\]?/);
    if (indexMatch) {
      return { click_element_by_index: { index: parseInt(indexMatch[1], 10) } };
    }
  }

  if (hints.includes("login") || hints.includes("navigate") || hints.includes("go to")) {
    const pages = ["dashboard", "trading", "agents", "analytics", "reports", "monitoring", "settings", "backtesting", "strategy-tutor", "login", "register", "home"];
    for (const page of pages) {
      if (hints.includes(page)) {
        return { navigate_to_page: { page } };
      }
    }
    return { done: { text: `I found something relevant: ${args.next_goal || "the page you're looking for"}`, success: true } };
  }

  if (hints.includes("scroll")) {
    return { scroll: { direction: hints.includes("up") ? "up" : "down" } };
  }

  if (hints.includes("type") || hints.includes("input") || hints.includes("fill")) {
    return { done: { text: "Please specify what text to enter and in which field.", success: true } };
  }

  // Default: respond with whatever insight the model provided
  return {
    done: {
      text: (args.next_goal as string) || "I wasn't sure what action to take. Please rephrase your request.",
      success: true,
    },
  };
}

// All known page names → canonical name used in ALLOWED_ROUTES
const PAGE_ALIASES: Record<string, string> = {
  "/dashboard": "dashboard", dashboard: "dashboard",
  "/trading": "trading", trading: "trading",
  "/agents": "agents", agents: "agents", "signal lab": "agents",
  "/analytics": "analytics", analytics: "analytics",
  "/reports": "reports", reports: "reports",
  "/strategy-tutor": "strategy-tutor", "strategy tutor": "strategy-tutor", "strategy-tutor": "strategy-tutor", tutor: "strategy-tutor",
  "/backtesting": "backtesting", backtesting: "backtesting",
  "/monitoring": "monitoring", monitoring: "monitoring",
  "/settings": "settings", settings: "settings",
  "/login": "login", login: "login", signin: "login", "sign in": "login",
  "/register": "register", register: "register", signup: "register",
  "/": "home", home: "home", landing: "home",
};

/**
 * Normalise navigate_to_page params. Model uses many parameter names:
 *   url, page_path, destination, page_name, href, path, route, target
 * Also strips trailing "page", "section", "area", "module" and leading # / . /
 */
function normaliseNavParams(params: Record<string, unknown>): Record<string, unknown> {
  function cleanPageName(raw: string): string {
    return raw
      .replace(/^[./#!]+/, "")           // strip leading . / # !
      .toLowerCase()
      .trim()
      .replace(/\s+(page|section|area|module|screen|view)$/, "")  // strip trailing words
      .trim();
  }

  if (typeof params.page === "string") {
    const raw = cleanPageName(params.page);
    const canonical = PAGE_ALIASES[raw] ?? PAGE_ALIASES["/" + raw] ?? raw;
    return { page: canonical };
  }

  const altKeys = ["url", "page_path", "destination", "page_name", "href", "path", "route", "target", "name"];
  for (const k of altKeys) {
    if (typeof params[k] === "string") {
      const raw = cleanPageName(params[k] as string);
      const canonical = PAGE_ALIASES[raw] ?? PAGE_ALIASES["/" + raw] ?? raw;
      return { page: canonical };
    }
  }

  return params;
}

/**
 * Sanitise done.text — small models often put a tool/function name,
 * a single keyword, or a raw JSON object instead of a real answer.
 */
function sanitiseDoneText(text: unknown): string {
  if (typeof text !== "string" || text.trim() === "") {
    return "I processed your request. Please ask a follow-up if you need more detail.";
  }
  const t = text.trim();

  // If text is a JSON string, try to extract a readable field
  if (t.startsWith("{") || t.startsWith("[")) {
    try {
      const obj = JSON.parse(t);
      if (obj && typeof obj === "object") {
        // Look for common readable fields
        const readable = obj.body ?? obj.description ?? obj.content ??
          obj.text ?? obj.summary ?? obj.message ?? obj.answer;
        if (typeof readable === "string" && readable.trim().length > 10) {
          return readable.trim();
        }
        // Try parameters.body etc
        const params = obj.parameters ?? obj.params;
        if (params && typeof params === "object") {
          const inner = params.body ?? params.description ?? params.content ?? params.text;
          if (typeof inner === "string" && inner.trim().length > 10) {
            return inner.trim();
          }
        }
      }
    } catch { /* not JSON */ }
    // JSON we can't parse into readable text — strip and summarise
    return "I processed your request. Please ask a follow-up if you need more detail.";
  }

  // Single word or looks like a function/tool name — replace
  if (/^[a-z_]+$/.test(t) && t.length < 30) {
    return "I processed your request. Please ask a follow-up if you need more detail.";
  }

  // Strip HTML tags if present
  const stripped = t.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
  return stripped.length > 0 ? stripped : "I processed your request.";
}

/**
 * Coerce string values to their expected types inside action params.
 * page-agent uses Zod schemas that expect actual numbers / booleans,
 * but small models often return them as strings ("3" instead of 3).
 */
function coerceActionParams(action: Record<string, unknown>): Record<string, unknown> {
  const NUMERIC_FIELDS: Record<string, string[]> = {
    click_element_by_index: ["index"],
    scroll: ["amount"],
    scroll_horizontally: ["amount"],
    select_dropdown_option: ["index"],
    input_text: ["index"],
    highlight_element: ["durationMs"],
  };

  for (const [actionName, fields] of Object.entries(NUMERIC_FIELDS)) {
    const params = action[actionName];
    if (params && typeof params === "object") {
      const p = params as Record<string, unknown>;
      for (const field of fields) {
        if (typeof p[field] === "string") {
          const n = Number(p[field]);
          if (!isNaN(n)) p[field] = n;
        }
      }
    }
  }
  return action;
}

/**
 * Master post-processing pass on an action object:
 * 1. Normalise navigate_to_page params (url/page_path/etc → page)
 * 2. Convert navigate_to_page with unknown page → done fallback
 * 3. Coerce numeric fields
 * 4. Sanitise done.text (replace single-word / tool-name garbage)
 * 5. Convert done.text that looks like "navigate_to_page, X" → actual navigate
 * 6. Replace highlight_element with no valid selector → done fallback
 */
function normaliseAndCoerceAction(action: Record<string, unknown>): Record<string, unknown> {
  // 1. navigate_to_page param normalisation
  if (action["navigate_to_page"] && typeof action["navigate_to_page"] === "object") {
    action["navigate_to_page"] = normaliseNavParams(action["navigate_to_page"] as Record<string, unknown>);
    // 2. If page is still unknown (not in PAGE_ALIASES values), convert to done
    const nav = action["navigate_to_page"] as Record<string, unknown>;
    const knownPages = new Set(Object.values(PAGE_ALIASES));
    if (typeof nav.page === "string" && !knownPages.has(nav.page)) {
      // anchor, garbage, or unrecognised destination — convert to done
      return { done: { text: "I couldn't find that page. Available pages: dashboard, trading, agents, analytics, backtesting, strategy-tutor, monitoring, settings, login.", success: false } };
    }
  }

  // 3. Numeric coercion
  action = coerceActionParams(action);

  // 4. Sanitise done.text
  if (action["done"] && typeof action["done"] === "object") {
    const done = action["done"] as Record<string, unknown>;
    const rawText = done.text;
    done.text = sanitiseDoneText(rawText);

    // 5. If done.text mentions a navigate intent, convert to actual navigation
    if (typeof done.text === "string") {
      const lowerText = done.text.toLowerCase();
      if (lowerText.includes("navigate_to_page") || lowerText.startsWith("navigate to")) {
        const pages = Object.keys(PAGE_ALIASES);
        for (const pg of pages) {
          if (lowerText.includes(pg)) {
            return { navigate_to_page: { page: PAGE_ALIASES[pg] ?? pg } };
          }
        }
      }
    }
  }

  // 6. highlight_element with no valid selector → done fallback
  if (action["highlight_element"] && typeof action["highlight_element"] === "object") {
    const hl = action["highlight_element"] as Record<string, unknown>;
    if (!hl.selector || typeof hl.selector !== "string") {
      return { done: { text: "I identified the relevant area on the page.", success: true } };
    }
  }

  return action;
}

async function proxyToOllama(
  req: NextRequest,
  pathSegments: string[]
): Promise<NextResponse> {
  const pathString = pathSegments.join("/");

  // Security: only allow known LLM API paths
  const isAllowed = ALLOWED_SEGMENTS.some(
    (allowed) => pathString === allowed || pathString.startsWith(allowed + "/")
  );
  if (!isAllowed) {
    return NextResponse.json({ error: "Forbidden path" }, { status: 403 });
  }

  const targetUrl = `${OLLAMA_BASE_URL}/${pathString}`;

  let body: string | undefined;
  if (req.method === "POST") {
    try {
      const json = await req.json();
      if (json && typeof json === "object") {
        json.model = process.env.OLLAMA_MODEL ?? "llama3.2:3b";
        if (pathString === "chat/completions") {
          // Force non-streaming: small models produce incomplete SSE chunks
          json.stream = false;
          // Do NOT override tool_choice — page-agent sends the correct named
          // {"type":"function","function":{"name":"AgentOutput"}} which forces
          // llama3.2:3b to generate a proper tool_call.
        }
      }
      body = JSON.stringify(json);
    } catch {
      return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
    }
  }

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
      },
      body,
      // @ts-expect-error — Next.js edge-compatible fetch
      duplex: "half",
    });

    const contentType = upstream.headers.get("content-type") ?? "";
    const isStream = contentType.includes("text/event-stream");

    if (isStream && upstream.body) {
      return new NextResponse(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    const data = await upstream.text();

    // ── Patch malformed responses from small local models ──────────────────
    let patched = data;
    if (pathString === "chat/completions" && upstream.ok) {
      try {
        const parsed = JSON.parse(data) as {
          choices?: Array<{
            finish_reason?: string;
            message?: {
              content?: string | null;
              tool_calls?: Array<{
                id: string;
                type: string;
                function: { name: string; arguments: string };
              }>;
            };
          }>;
        };
        const choice = parsed?.choices?.[0];
        const msg = choice?.message;

        // Case 1: Empty response — inject a graceful "done" fallback
        if (
          msg &&
          (msg.content == null || msg.content === "") &&
          (!msg.tool_calls || msg.tool_calls.length === 0)
        ) {
          const fallbackArgs = JSON.stringify({
            evaluation_previous_goal: "Model returned an empty response.",
            memory: "Unable to determine a useful action.",
            next_goal: "Inform the user and stop.",
            action: {
              done: {
                text: "I couldn't process that request. Please rephrase or try a simpler task.",
                success: false,
              },
            },
          });
          msg.tool_calls = [
            {
              id: "fallback_0",
              type: "function",
              function: { name: "AgentOutput", arguments: fallbackArgs },
            },
          ];
          if (choice) choice.finish_reason = "tool_calls";
        }

        // Known valid tool names for validation:
        const VALID_ACTIONS = new Set([
          "done", "wait", "click_element_by_index", "input_text",
          "select_dropdown_option", "scroll", "scroll_horizontally",
          "navigate_to_page", "highlight_element", "fetch_market_signals",
          "request_confirmation",
        ]);

        // Case 2: Content present but NO tool_calls.
        // Handles: JSON content AND plain-text content.
        if (
          msg &&
          msg.content &&
          msg.content.trim().length > 0 &&
          (!msg.tool_calls || msg.tool_calls.length === 0)
        ) {
          let agentOutputArgs: Record<string, unknown>;

          try {
            const contentJson = JSON.parse(msg.content.trim());

            if (
              contentJson &&
              typeof contentJson === "object" &&
              (contentJson.action || contentJson.evaluation_previous_goal || contentJson.next_goal)
            ) {
              // Model returned something close to AgentOutput format
              agentOutputArgs = {
                evaluation_previous_goal: contentJson.evaluation_previous_goal ?? "none",
                memory: contentJson.memory ?? "",
                next_goal: contentJson.next_goal ?? "Proceeding with the task.",
                action: contentJson.action ?? { done: { text: "Task complete.", success: true } },
              };
            } else if (
              contentJson &&
              typeof contentJson === "object" &&
              typeof contentJson.name === "string"
            ) {
              // Model returned {"name":"tool_name","parameters":{...}} format
              const toolName = contentJson.name;
              const toolParams = contentJson.parameters ?? contentJson.arguments ?? {};
              const normalizedAction = VALID_ACTIONS.has(toolName)
                ? { [toolName]: typeof toolParams === "object" ? toolParams : {} }
                : inferActionFromContext({ next_goal: toolName, action: { [toolName]: toolParams } });
              agentOutputArgs = {
                evaluation_previous_goal: "Parsed from model content response.",
                memory: "",
                next_goal: toolName,
                action: normalizedAction,
              };
            } else {
              // Unknown JSON structure — wrap as done
              agentOutputArgs = {
                evaluation_previous_goal: "Model returned unrecognized JSON.",
                memory: "",
                next_goal: "Inform the user.",
                action: {
                  done: {
                    text: typeof contentJson === "string" ? contentJson : JSON.stringify(contentJson),
                    success: true,
                  },
                },
              };
            }
          } catch {
            // Content is plain text (not JSON) — wrap as done response
            agentOutputArgs = {
              evaluation_previous_goal: "Model returned a plain text response.",
              memory: "",
              next_goal: "Reply to user.",
              action: {
                done: {
                  text: msg.content.trim(),
                  success: true,
                },
              },
            };
          }

          // Normalize action field
          if (agentOutputArgs.action && typeof agentOutputArgs.action === "object") {
            const action = agentOutputArgs.action as Record<string, unknown>;
            if ("name" in action && typeof action.name === "string") {
              const actionName = action.name as string;
              const actionParams = (action.parameters ?? action.arguments ?? {}) as Record<string, unknown>;
              agentOutputArgs.action = VALID_ACTIONS.has(actionName)
                ? { [actionName]: typeof actionParams === "object" ? actionParams : {} }
                : inferActionFromContext({ next_goal: actionName, action: { [actionName]: actionParams } });
            }
          }

          // Normalise navigate_to_page params and coerce numbers
          if (agentOutputArgs.action && typeof agentOutputArgs.action === "object") {
            agentOutputArgs.action = normaliseAndCoerceAction(
              agentOutputArgs.action as Record<string, unknown>
            );
          }

          msg.tool_calls = [
            {
              id: "content_to_tc_0",
              type: "function",
              function: {
                name: "AgentOutput",
                arguments: JSON.stringify(agentOutputArgs),
              },
            },
          ];
          msg.content = null;
          if (choice) choice.finish_reason = "tool_calls";
        }

        // Case 3: Tool call exists — normalize the "action" field.
        const tc = msg?.tool_calls?.[0];
        if (tc?.function?.arguments) {
          try {
            // If the model returned a direct tool call (e.g. navigate_to_page, done, highlight_element)
            // instead of the expected AgentOutput wrapper, convert it to AgentOutput format.
            if (tc.function.name && tc.function.name !== "AgentOutput") {
              const directToolName = tc.function.name;
              let directArgs: Record<string, unknown> = {};
              try { directArgs = JSON.parse(tc.function.arguments); } catch { /* ignore */ }
              const action = VALID_ACTIONS.has(directToolName)
                ? { [directToolName]: directArgs }
                : { done: { text: JSON.stringify(directArgs) || directToolName, success: true } };
              const wrapped = {
                evaluation_previous_goal: "Model returned direct tool call.",
                memory: "",
                next_goal: directToolName,
                action: normaliseAndCoerceAction(action),
              };
              tc.function.name = "AgentOutput";
              tc.function.arguments = JSON.stringify(wrapped);
              if (choice) choice.finish_reason = "tool_calls";
            } else {
            const args = JSON.parse(tc.function.arguments);
            let needsRewrite = false;

            if (args.action && typeof args.action === "object") {
              const actionKeys = Object.keys(args.action);
              const firstKey = actionKeys[0];

              if ("name" in args.action && typeof args.action.name === "string") {
                const actionName = args.action.name;
                const actionParams = args.action.parameters ?? args.action.arguments ?? {};
                args.action = { [actionName]: typeof actionParams === "object" ? actionParams : {} };
                needsRewrite = true;
              } else if (firstKey && !VALID_ACTIONS.has(firstKey)) {
                const inferredAction = inferActionFromContext(args);
                args.action = inferredAction;
                needsRewrite = true;
              }

              // Fix primitive action values: {"click_element_by_index": 5} → {"click_element_by_index": {"index": 5}}
              const finalKey = Object.keys(args.action)[0];
              const finalVal = args.action[finalKey];
              if (finalVal !== null && finalVal !== undefined && typeof finalVal !== "object") {
                args.action[finalKey] = { index: finalVal };
                needsRewrite = true;
              }
            } else if (typeof args.action === "string") {
              if (VALID_ACTIONS.has(args.action)) {
                args.action = { [args.action]: {} };
              } else {
                args.action = { done: { text: args.action, success: true } };
              }
              needsRewrite = true;
            } else if (!args.action) {
              args.action = {
                done: { text: "I wasn't sure what action to take. Please rephrase.", success: false },
              };
              needsRewrite = true;
            }

            // Normalise navigate_to_page params, coerce numbers, sanitise done.text
            if (args.action && typeof args.action === "object") {
              const before = JSON.stringify(args.action);
              args.action = normaliseAndCoerceAction(args.action as Record<string, unknown>);
              if (JSON.stringify(args.action) !== before) needsRewrite = true;
            }

            if (needsRewrite) {
              tc.function.arguments = JSON.stringify(args);
            }
            } // end else (AgentOutput case)
          } catch {
            // arguments not valid JSON — leave as-is
          }
        }

        patched = JSON.stringify(parsed);
      } catch {
        // response not valid JSON — leave as-is
      }
    }

    return new NextResponse(patched, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Upstream LLM unavailable";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
