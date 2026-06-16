/**
 * Next.js proxy for Django's /api/ticks endpoint.
 * Avoids CORS by routing browser requests through the Next.js server (same-origin).
 */
import { NextResponse } from "next/server";

const DJANGO = (process.env.DJANGO_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

// Cache ticks for 10 seconds server-side to reduce Django calls
let _cache: Record<string, unknown> = {};
let _cacheTs = 0;

export async function GET() {
    const now = Date.now();
    if (now - _cacheTs < 10000 && Object.keys(_cache).length > 0) {
        return NextResponse.json(_cache);
    }
    try {
        const res = await fetch(`${DJANGO}/api/ticks`, {
            cache: "no-store",
            signal: AbortSignal.timeout(15000),
        });
        if (!res.ok) {
            // Return stale cache if available, otherwise empty
            return NextResponse.json(_cache);
        }
        const data = (await res.json()) as Record<string, unknown>;
        if (Object.keys(data).length > 0) {
            _cache = data;
            _cacheTs = now;
        }
        return NextResponse.json(_cache);
    } catch {
        return NextResponse.json(_cache);
    }
}
