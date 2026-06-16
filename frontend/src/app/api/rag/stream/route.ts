import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getDjangoAuthHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export const maxDuration = 120;
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions);
    const authHeader = getDjangoAuthHeader(req);

    if (!session?.user?.email || !authHeader) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
        });
    }

    // Safely read body — guard against empty/non-JSON payloads
    let query: string | undefined;
    try {
        const body = await req.json() as { query?: string };
        query = typeof body.query === "string" ? body.query.trim() : undefined;
    } catch {
        return new Response(JSON.stringify({ error: "Invalid request body." }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
        });
    }

    if (!query || query.length < 3) {
        return new Response(JSON.stringify({ error: "Query must be at least 3 characters." }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
        });
    }

    const upstream = await fetch(`${DJANGO}/api/tutor/rag/stream/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: authHeader,
        },
        body: JSON.stringify({ query }),
    }).catch(() => null);

    if (!upstream || !upstream.ok || !upstream.body) {
        // Surface the actual Django error body so it's visible in the browser
        const errText = upstream ? await upstream.text().catch(() => "") : "";
        let errData: Record<string, unknown>;
        try { errData = JSON.parse(errText); }
        catch { errData = { error: errText || "Stream failed." }; }
        return new Response(JSON.stringify(errData), {
            status: upstream?.status ?? 502,
            headers: { "Content-Type": "application/json" },
        });
    }

    return new Response(upstream.body, {
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    });
}
