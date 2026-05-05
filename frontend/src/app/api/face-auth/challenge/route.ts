import { NextRequest, NextResponse } from "next/server";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
    // Forward browser cookies (Django sessionid) so Django can read the session
    const cookie = req.headers.get("cookie") ?? "";
    const res = await fetch(`${DJANGO}/api/face-auth/liveness/challenge/`, {
        headers: cookie ? { cookie } : {},
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
}
