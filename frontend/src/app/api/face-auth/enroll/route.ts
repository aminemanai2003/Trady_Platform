import { NextRequest, NextResponse } from "next/server";
import { getDjangoAuthHeader, getForwardedCookieHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

// Allow up to 120 seconds — DeepFace may download model weights on first use
export const maxDuration = 120;

export async function POST(req: NextRequest) {
    try {
        const body = await req.json().catch(() => ({}));
        const authHeader = getDjangoAuthHeader(req);
        const cookie = getForwardedCookieHeader(req);

        // Forward the browser's AbortSignal so that if the client times out,
        // the upstream Django request is also cancelled immediately.
        const res = await fetch(`${DJANGO}/api/face-auth/enroll/`, {
            method: "POST",
            signal: req.signal,
            headers: {
                "Content-Type": "application/json",
                ...(authHeader ? { Authorization: authHeader } : {}),
                ...(cookie ? { cookie } : {}),
            },
            body: JSON.stringify(body),
        });
        const data = await res.json().catch(() => ({
            success: false,
            detail: "Invalid response from authentication server.",
        }));
        return NextResponse.json(data, { status: res.status });
    } catch (err: unknown) {
        // AbortError = client cancelled (timeout) — don't log as network error
        if (err instanceof Error && err.name === "AbortError") {
            return NextResponse.json(
                { success: false, reason: "timeout", detail: "The AI model is still initialising. Please wait a moment and try again." },
                { status: 503 }
            );
        }
        return NextResponse.json(
            { success: false, reason: "network_error", detail: "Could not reach the authentication server. Make sure the backend is running." },
            { status: 503 }
        );
    }
}
