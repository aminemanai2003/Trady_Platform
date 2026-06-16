import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ensureUserSubscription } from "@/lib/billing";

function getUserId(session: unknown): string | null {
    return (session as { user?: { id?: string } } | null)?.user?.id ?? null;
}

export async function GET() {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);

    if (!userId) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const subscription = await ensureUserSubscription(userId);
    return NextResponse.json({ subscription });
}
