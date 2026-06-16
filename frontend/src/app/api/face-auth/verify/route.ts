import { NextRequest, NextResponse } from "next/server";
import {
    appendUpstreamSetCookie,
    getForwardedCookieHeader,
    setDjangoTokenCookie,
} from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

// Allow up to 120 seconds — face model inference can be slow
export const maxDuration = 120;

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));

    // Forward browser cookies (Django sessionid) so Django can resolve
    // the pending_2fa_user_id stored in the server-side session.
    const cookie = getForwardedCookieHeader(req);

    const res = await fetch(`${DJANGO}/api/face-auth/verify/`, {
        method: "POST",
        signal: req.signal,
        headers: {
            "Content-Type": "application/json",
            ...(cookie ? { cookie } : {}),
        },
        body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({
        verified: false,
        reason: "parse_error",
        detail: "Invalid response from authentication server.",
    }));
    const response = NextResponse.json(data, { status: res.status });
    appendUpstreamSetCookie(response, res.headers.get("set-cookie"));
    setDjangoTokenCookie(response, data.token);
    return response;
}
