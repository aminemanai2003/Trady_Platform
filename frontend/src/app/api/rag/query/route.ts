import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getDjangoAuthHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

export const maxDuration = 60;

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    const session = await getServerSession(authOptions);
    const authHeader = getDjangoAuthHeader(req);

    if (!session?.user?.email || !authHeader) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { query } = body as { query?: string };

    const res = await fetch(`${DJANGO}/api/tutor/rag/query/`, {
        method:  "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: authHeader,
        },
        body:    JSON.stringify({ query }),
    });

    const data = await res.json().catch(() => ({ error: "Query failed." }));
    return NextResponse.json(data, { status: res.status });
}
