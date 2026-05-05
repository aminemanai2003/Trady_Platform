import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getDjangoAuthHeader } from "@/lib/django-auth";

const DJANGO = process.env.DJANGO_API_URL ?? "http://localhost:8000";

// Allow up to 60 s for embedding generation during upload
export const maxDuration = 60;

export async function POST(req: NextRequest) {
    const formData = await req.formData().catch(() => null);
    const session = await getServerSession(authOptions);
    const authHeader = getDjangoAuthHeader(req);

    if (!formData) {
        return NextResponse.json({ error: "Invalid form data." }, { status: 400 });
    }

    if (!session?.user?.email || !authHeader) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    formData.delete("user_email");

    const res = await fetch(`${DJANGO}/api/tutor/documents/upload/`, {
        method: "POST",
        headers: { Authorization: authHeader },
        body:   formData,
    });

    const data = await res.json().catch(() => ({ error: "Upload failed." }));
    return NextResponse.json(data, { status: res.status });
}
