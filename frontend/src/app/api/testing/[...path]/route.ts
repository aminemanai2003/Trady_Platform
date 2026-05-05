/**
 * Next.js proxy for Django's /api/testing/* endpoints.
 * Avoids CORS by routing browser requests through the Next.js server (same-origin).
 * Handles: trades (GET/POST), trades/:id/close (PATCH), summary, reset, coach
 */
import { NextRequest, NextResponse } from "next/server";

const DJANGO = (process.env.DJANGO_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
) {
    const { path } = await params;
    const tail = path.join("/");
    const search = request.nextUrl.search ?? "";
    try {
        const res = await fetch(`${DJANGO}/api/testing/${tail}${search}`, {
            cache: "no-store",
            signal: AbortSignal.timeout(15000),
        });
        const data = await res.json();
        return NextResponse.json(data, { status: res.status });
    } catch {
        return NextResponse.json({ detail: "upstream error" }, { status: 502 });
    }
}

export async function POST(
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
) {
    const { path } = await params;
    const tail = path.join("/");
    try {
        const body = await request.json().catch(() => ({}));
        const res = await fetch(`${DJANGO}/api/testing/${tail}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(15000),
        });
        const data = await res.json();
        return NextResponse.json(data, { status: res.status });
    } catch {
        return NextResponse.json({ detail: "upstream error" }, { status: 502 });
    }
}

export async function PATCH(
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
) {
    const { path } = await params;
    const tail = path.join("/");
    try {
        const body = await request.json().catch(() => ({}));
        const res = await fetch(`${DJANGO}/api/testing/${tail}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(15000),
        });
        const data = await res.json();
        return NextResponse.json(data, { status: res.status });
    } catch {
        return NextResponse.json({ detail: "upstream error" }, { status: 502 });
    }
}
