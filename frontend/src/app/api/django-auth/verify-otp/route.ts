import { NextRequest, NextResponse } from "next/server";
import {
    appendUpstreamSetCookie,
    getForwardedCookieHeader,
    setDjangoTokenCookie,
} from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    const cookie = getForwardedCookieHeader(req);
    const res = await fetch(`${DJANGO}/api/auth/verify-otp/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(cookie ? { cookie } : {}),
        },
        body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({
        success: false,
        message: "Authentication server returned an unexpected response.",
    }));
    const response = NextResponse.json(data, { status: res.status });
    appendUpstreamSetCookie(response, res.headers.get("set-cookie"));
    setDjangoTokenCookie(response, data.token);
    return response;
}
