import { NextRequest, NextResponse } from "next/server";

/**
 * LLM Proxy — routes page-agent requests to Ollama (local).
 * API keys never exposed to the client.
 *
 * Ollama endpoint: OLLAMA_BASE_URL (default: http://localhost:11434/v1)
 * Model:          OLLAMA_MODEL    (default: qwen3:14b)
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";

const ALLOWED_PATHS = ["/chat/completions", "/models"];

export async function POST(req: NextRequest) {
  return proxyToOllama(req, "/chat/completions");
}

export async function GET(req: NextRequest) {
  const urlPath = new URL(req.url).searchParams.get("path") ?? "/models";
  if (!ALLOWED_PATHS.includes(urlPath)) {
    return NextResponse.json({ error: "Forbidden path" }, { status: 403 });
  }
  return proxyToOllama(req, urlPath);
}

async function proxyToOllama(
  req: NextRequest,
  path: string
): Promise<NextResponse> {
  const targetUrl = `${OLLAMA_BASE_URL}${path}`;

  let body: string | undefined;
  if (req.method === "POST") {
    try {
      const json = await req.json();
      // Inject model from env if client didn't specify (or override client choice)
      if (json && typeof json === "object") {
        json.model = process.env.OLLAMA_MODEL ?? "qwen2.5:3b";
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
        // Ollama doesn't require Authorization — omit the header entirely
        // to avoid leaking any token accidentally set by the client
      },
      body,
      // Forward streaming for SSE responses
      // @ts-expect-error — Next.js edge-compatible fetch
      duplex: "half",
    });

    const isStream =
      upstream.headers.get("content-type")?.includes("text/event-stream") ??
      false;

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
    return new NextResponse(data, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Upstream LLM unavailable";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
