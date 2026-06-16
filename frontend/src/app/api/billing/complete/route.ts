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

    const secretKey = process.env.STRIPE_SECRET_KEY;
    if (!secretKey) {
        return NextResponse.json({ error: "Stripe is not configured" }, { status: 500 });
    }

    const body = await req.json().catch(() => null);
    const sessionId = typeof body?.sessionId === "string" ? body.sessionId : null;

    if (!sessionId || !sessionId.startsWith("cs_")) {
        return NextResponse.json({ error: "Invalid checkout session" }, { status: 400 });
    }

    const stripeResponse = await fetch(`https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(sessionId)}`, {
        headers: { Authorization: `Bearer ${secretKey}` },
    });

    const checkoutSession = await stripeResponse.json();
    if (!stripeResponse.ok) {
        return NextResponse.json(
            { error: checkoutSession.error?.message || "Unable to verify Stripe checkout" },
            { status: stripeResponse.status }
        );
    }

    if (checkoutSession.client_reference_id !== userId || checkoutSession.metadata?.userId !== userId) {
        return NextResponse.json({ error: "Checkout session does not belong to this user" }, { status: 403 });
    }

    if (checkoutSession.status !== "complete" || checkoutSession.payment_status !== "paid") {
        return NextResponse.json({ error: "Checkout has not been paid yet" }, { status: 402 });
    }

    const plan = normalizePlan(checkoutSession.metadata?.plan);
    if (plan !== "plus" && plan !== "pro") {
        return NextResponse.json({ error: "Invalid checkout plan" }, { status: 400 });
    }

    const billingInterval = normalizeBillingInterval(checkoutSession.metadata?.billingInterval);
    const subscription = await setUserSubscriptionPlan(userId, plan, billingInterval, {
        stripeCustomerId: typeof checkoutSession.customer === "string" ? checkoutSession.customer : null,
        stripeSubscriptionId: typeof checkoutSession.subscription === "string" ? checkoutSession.subscription : null,
    });

    return NextResponse.json({ subscription });
}
