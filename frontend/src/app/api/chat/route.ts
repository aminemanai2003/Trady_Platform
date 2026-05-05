import { NextRequest, NextResponse } from "next/server";

/**
 * /api/chat — conversational LLM endpoint.
 *
 * Pipeline: User text (no /agent prefix) → here → Ollama (LLaMA 3.2 3B) → SSE stream.
 *
 * Constraints:
 *  - No tool execution
 *  - No UI state mutation
 *  - Concise replies (system prompt enforces this)
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

const CHAT_MODEL = process.env.OLLAMA_CHAT_MODEL ?? "llama3.2:3b";

const SYSTEM_PROMPT = `You are Trady's conversational assistant for a forex trading platform.

Hard rules:
- Reply in 1-4 sentences. Be direct.
- You do NOT execute actions. You do NOT navigate. You do NOT click anything.
- If the user asks you to perform an action (navigate, click, run a task), tell them to prefix the command with "/agent" — e.g. "/agent take me to login".
- Never invent routes, page names, or features that were not mentioned by the user or this prompt.
- Plain text only. No markdown headers, no code fences unless quoting code.

Trady context (use only what is relevant to the question):
- Multi-agent forex platform by team DATAMINDS (ESPRIT 2025).
- 3 AI agents: Technical (RSI/MACD/Bollinger), Macro (FRED data), Sentiment (FinBERT).
- 4 currency pairs: EUR/USD, USD/JPY, GBP/USD, USD/CHF.
- 5-year backtest: Sharpe 1.73, Win Rate 57%.
- Pages: Dashboard, Trading, Signal Lab, Analytics, Reports, Strategy Tutor, Backtesting.

If a question is outside this scope, say you only assist with the Trady platform.`;

interface ChatRequestBody {
  messages?: Array<{ role: "user" | "assistant"; content: string }>;
}

export async function POST(req: NextRequest): Promise<Response> {
  let body: ChatRequestBody;
  try {
    body = (await req.json()) as ChatRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const history = Array.isArray(body.messages) ? body.messages : [];
  if (history.length === 0) {
    return NextResponse.json({ error: "messages[] required" }, { status: 400 });
  }

  // Validate role/content shape — reject anything else
  const cleanHistory = history
    .filter(
      (m) =>
        m &&
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.length > 0
    )
    .slice(-12); // bound history to last 12 turns

  if (cleanHistory.length === 0) {
    return NextResponse.json({ error: "no valid messages" }, { status: 400 });
  }

  const upstream = await fetch(`${OLLAMA_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: CHAT_MODEL,
      stream: true,
      temperature: 0.4,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        ...cleanHistory,
      ],
    }),
  }).catch((err: unknown) => {
    console.error("[/api/chat] upstream fetch failed:", err);
    return null;
  });

  if (!upstream || !upstream.ok || !upstream.body) {
    const status = upstream?.status ?? 502;
    const reason = upstream ? await upstream.text().catch(() => "") : "upstream unreachable";
    console.error(`[/api/chat] upstream error ${status}: ${reason}`);
    return NextResponse.json(
      { error: "Chat backend unavailable" },
      { status: 502 }
    );
  }

  // Forward SSE directly to the client
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
