import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { normalizeBillingInterval, normalizePlan, setUserSubscriptionPlan } from "@/lib/billing";

function getUserId(session: unknown): string | null {
    return (session as { user?: { id?: string } } | null)?.user?.id ?? null;
}

export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);

    if (!userId) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json().catch(() => null);
    const plan = normalizePlan(body?.plan);

    if (!plan) {
        return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    if (plan !== "basic") {
        return NextResponse.json({ error: "Paid plans must use Stripe Checkout" }, { status: 400 });
    }

    const billingInterval = normalizeBillingInterval(body?.billingInterval);
    const subscription = await setUserSubscriptionPlan(userId, plan, billingInterval);

    return NextResponse.json({ subscription });
}
