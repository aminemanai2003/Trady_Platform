import { NextRequest, NextResponse } from "next/server";
import { getDjangoAuthHeader, getForwardedCookieHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    const authHeader = getDjangoAuthHeader(req);
    const cookie = getForwardedCookieHeader(req);

    // 120s timeout for face verification (AI model may need time)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    try {
        const res = await fetch(`${DJANGO}/api/auth/verify-2fa-setup/`, {
            method: "POST",
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                ...(authHeader ? { Authorization: authHeader } : {}),
                ...(cookie ? { cookie } : {}),
            },
            body: JSON.stringify(body),
        });
        clearTimeout(timeoutId);

        const data = await res.json();
        const response = NextResponse.json(data, { status: res.status });

        // Forward Django set-cookie headers back to client
        const setCookieHeader = res.headers.get("set-cookie");
        if (setCookieHeader) {
            response.headers.set("set-cookie", setCookieHeader);
        }

        return response;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === "AbortError") {
            return NextResponse.json(
                { success: false, verified: false, message: "Verification timeout. Please try again." },
                { status: 504 }
            );
        }
        return NextResponse.json(
            { success: false, verified: false, message: "Network error during verification." },
            { status: 500 }
        );
    }
}
