import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getPlanEntitlements, getUserPlan } from "@/lib/billing";

const API_URL = process.env.DJANGO_API_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = (session?.user as { id?: string } | undefined)?.id;
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const pair = (request.nextUrl.searchParams.get("pair") || "EURUSD").toUpperCase();
    const timeframe = (request.nextUrl.searchParams.get("timeframe") || "1h").toLowerCase();
    const plan = await getUserPlan(userId);
    const entitlements = getPlanEntitlements(plan);
    if (!entitlements.signalPairs.includes(pair)) {
        return NextResponse.json(
            { error: `${pair} is not included in ${entitlements.label}` },
            { status: 403 },
        );
    }

    const upstream = await fetch(
        `${API_URL}/api/v2/market/candles/?pair=${encodeURIComponent(pair)}&timeframe=${encodeURIComponent(timeframe)}&limit=600`,
        { cache: "no-store", signal: AbortSignal.timeout(30000) },
    );
    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status });
}
