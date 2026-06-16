import { NextRequest, NextResponse } from "next/server";
import { setDjangoTokenCookie } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json().catch(() => ({}));
        const res = await fetch(`${DJANGO}/api/auth/django-register/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json().catch(() => ({
            success: false,
            message: "Invalid response from authentication server.",
        }));
        const response = NextResponse.json(data, { status: res.status });
        setDjangoTokenCookie(response, data.token);
        return response;
    } catch {
        return NextResponse.json(
            { success: false, message: "Could not reach the authentication server." },
            { status: 503 }
        );
    }
}
