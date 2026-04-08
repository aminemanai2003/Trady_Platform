import { NextRequest, NextResponse } from "next/server";
import { getDjangoAuthHeader, getForwardedCookieHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
    const authHeader = getDjangoAuthHeader(req);
    const cookie = getForwardedCookieHeader(req);
    const res = await fetch(`${DJANGO}/api/auth/2fa/setup/`, {
        headers: {
            ...(authHeader ? { Authorization: authHeader } : {}),
            ...(cookie ? { cookie } : {}),
        },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
}

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    const authHeader = getDjangoAuthHeader(req);
    const cookie = getForwardedCookieHeader(req);
    const res = await fetch(`${DJANGO}/api/auth/2fa/setup/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(authHeader ? { Authorization: authHeader } : {}),
            ...(cookie ? { cookie } : {}),
        },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
}
