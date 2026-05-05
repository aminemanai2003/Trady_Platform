/**
 * chat-client.ts
 * Client-side streaming helper for /api/chat (LLM chat pipeline).
 *
 * Consumes the OpenAI-compatible SSE stream forwarded from Ollama and yields
 * incremental text deltas. The caller is responsible for accumulating them
 * into a final message and updating UI state.
 */

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface StreamHandlers {
  onDelta: (chunk: string) => void;
  onDone?: (full: string) => void;
  onError?: (err: Error) => void;
}

/**
 * Stream a chat completion. Resolves once the stream ends (or aborts).
 * Returns the full assembled response on success.
 */
export async function streamChat(
  messages: ChatMessage[],
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    const err = new Error(`Chat API ${res.status}: ${text || res.statusText}`);
    handlers.onError?.(err);
    throw err;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames separated by "\n\n"
      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        sep = buffer.indexOf("\n\n");

        for (const line of frame.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          if (payload === "[DONE]") {
            handlers.onDone?.(full);
            return full;
          }
          try {
            const json = JSON.parse(payload) as {
              choices?: Array<{ delta?: { content?: string } }>;
            };
            const delta = json.choices?.[0]?.delta?.content;
            if (typeof delta === "string" && delta.length > 0) {
              full += delta;
              handlers.onDelta(delta);
            }
          } catch {
            // Ignore malformed frames — Ollama occasionally sends keep-alives
          }
        }
      }
    }
  } catch (err) {
    if (signal?.aborted) {
      handlers.onDone?.(full);
      return full;
    }
    const error = err instanceof Error ? err : new Error("Stream read error");
    handlers.onError?.(error);
    throw error;
  }

  handlers.onDone?.(full);
  return full;
}
