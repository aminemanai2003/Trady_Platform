import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getDjangoAuthHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

async function getAuthenticatedEmail() {
    const session = await getServerSession(authOptions);
    const email = session?.user?.email?.trim().toLowerCase();
    return email && email.includes("@") ? email : "";
}

export async function GET(req: NextRequest) {
    const userEmail = await getAuthenticatedEmail();
    const authHeader = getDjangoAuthHeader(req);

    if (!userEmail || !authHeader) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const res = await fetch(
        `${DJANGO}/api/tutor/documents/`,
        {
            cache: "no-store",
            headers: { Authorization: authHeader },
        },
    );

    const data = await res.json().catch(() => ({ documents: [] }));
    return NextResponse.json(data, { status: res.status });
}

export async function DELETE(req: NextRequest) {
    const userEmail = await getAuthenticatedEmail();
    const authHeader = getDjangoAuthHeader(req);

    if (!userEmail || !authHeader) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json().catch(() => ({}));
    const { doc_id } = body as { doc_id?: string };

    const res = await fetch(
        `${DJANGO}/api/tutor/documents/${doc_id ?? ""}/`,
        {
            method: "DELETE",
            headers: { Authorization: authHeader },
        },
    );

    const data = await res.json().catch(() => ({ deleted: false }));
    return NextResponse.json(data, { status: res.status });
}
