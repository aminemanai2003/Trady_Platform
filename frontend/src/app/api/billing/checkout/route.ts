import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { normalizeBillingInterval, normalizePlan } from "@/lib/billing";

const checkoutPlans = {
    plus: {
        name: "Trady Plus",
        description: "Strategy Tutor image/audio, signal reports, and standard agent workflows.",
        displayMonthly: "29 TND",
        displayYearly: "290 TND",
        monthly: 900,
        yearly: 9_000,
    },
    pro: {
        name: "Trady Pro",
        description: "Full multimodal tutor including video, advanced monitoring, and premium research limits.",
        displayMonthly: "89 TND",
        displayYearly: "890 TND",
        monthly: 2_700,
        yearly: 27_000,
    },
} as const;

const checkoutCurrency = "eur";

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
    const plan = normalizePlan(body?.plan);
    const billingInterval = normalizeBillingInterval(body?.billingInterval);

    if (plan !== "plus" && plan !== "pro") {
        return NextResponse.json({ error: "Stripe checkout is only available for Plus and Pro" }, { status: 400 });
    }

    const selected = checkoutPlans[plan];
    const amount = selected[billingInterval];
    const origin = req.headers.get("origin") || process.env.NEXTAUTH_URL || "http://localhost:3000";
    const params = new URLSearchParams();

    params.set("mode", "subscription");
    params.set("success_url", `${origin}/billing?checkout=success&session_id={CHECKOUT_SESSION_ID}`);
    params.set("cancel_url", `${origin}/billing?checkout=cancelled`);
    params.set("client_reference_id", userId);
    params.set("metadata[userId]", userId);
    params.set("metadata[plan]", plan);
    params.set("metadata[billingInterval]", billingInterval);
    params.set("subscription_data[metadata][userId]", userId);
    params.set("subscription_data[metadata][plan]", plan);
    params.set("subscription_data[metadata][billingInterval]", billingInterval);
    params.set("line_items[0][quantity]", "1");
    params.set("line_items[0][price_data][currency]", checkoutCurrency);
    params.set("line_items[0][price_data][unit_amount]", String(amount));
    params.set("line_items[0][price_data][recurring][interval]", billingInterval === "yearly" ? "year" : "month");
    params.set(
        "line_items[0][price_data][product_data][name]",
        `${selected.name} - ${billingInterval === "yearly" ? selected.displayYearly : selected.displayMonthly} plan`
    );
    params.set("line_items[0][price_data][product_data][description]", selected.description);

    if (session?.user?.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(session.user.email)) {
        params.set("customer_email", session.user.email);
    }

    const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", {
        method: "POST",
        headers: {
            Authorization: `Bearer ${secretKey}`,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params,
    });

    const data = await stripeResponse.json();
    if (!stripeResponse.ok) {
        return NextResponse.json(
            { error: data.error?.message || "Stripe checkout failed", stripeError: data.error ?? null },
            { status: stripeResponse.status }
        );
    }

    return NextResponse.json({ url: data.url });
}
