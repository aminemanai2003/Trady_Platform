import { createHash, randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import {
    consumePlanUsage,
    getPlanEntitlements,
    getPlanUsage,
    getUserPlan,
    refundPlanUsage,
} from "@/lib/billing";

const API_URL = process.env.DJANGO_API_URL || "http://127.0.0.1:8000";
const FEATURE = "market_intelligence_analysis";

export async function GET() {
    const session = await getServerSession(authOptions);
    const userId = (session?.user as { id?: string } | undefined)?.id;
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const plan = await getUserPlan(userId);
    const entitlements = getPlanEntitlements(plan);
    const usage = await getPlanUsage(userId, FEATURE);
    return NextResponse.json({
        plan,
        planLabel: entitlements.label,
        pairs: entitlements.signalPairs,
        usage: { ...usage, limit: entitlements.signalGenerationsPerMonth },
    });
}

export async function POST(request: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = (session?.user as { id?: string } | undefined)?.id;
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await request.json();
    const pair = String(body.pair || "").toUpperCase();
    const timeframe = String(body.timeframe || "").toLowerCase();
    const screenshot = typeof body.screenshot === "string" ? body.screenshot : null;
    const plan = await getUserPlan(userId);
    const entitlements = getPlanEntitlements(plan);

    if (!entitlements.signalPairs.includes(pair)) {
        return NextResponse.json({ error: `${pair} is not included in ${entitlements.label}` }, { status: 403 });
    }
    if (!["1h", "4h", "1d"].includes(timeframe)) {
        return NextResponse.json({ error: "Unsupported timeframe" }, { status: 400 });
    }
    if (screenshot && screenshot.length > 7_000_000) {
        return NextResponse.json({ error: "Chart capture is too large" }, { status: 413 });
    }

    const usage = await consumePlanUsage(
        userId,
        FEATURE,
        entitlements.signalGenerationsPerMonth,
    );
    if (!usage.consumed) {
        return NextResponse.json(
            { error: "Monthly analysis limit reached", usage },
            { status: 429 },
        );
    }

    try {
        const upstream = await fetch(`${API_URL}/api/v2/market/analyze/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pair, timeframe, screenshot }),
            cache: "no-store",
            signal: AbortSignal.timeout(240000),
        });
        const result = await upstream.json();
        if (!upstream.ok) {
            await refundPlanUsage(userId, FEATURE);
            return NextResponse.json(result, { status: upstream.status });
        }

        const screenshotHash = screenshot
            ? createHash("sha256").update(screenshot).digest("hex")
            : null;
        const analysis = await prisma.marketAnalysis.create({
            data: {
                id: randomUUID(),
                userId,
                pair,
                timeframe,
                horizon: result.horizon,
                action: result.action,
                marketTimestamp: new Date(result.market_timestamp),
                dataSource: result.data_source,
                dataStatus: result.data_status,
                latestPrice: result.latest_price,
                screenshotHash,
                result,
            },
        });
        return NextResponse.json({
            ...result,
            analysisId: analysis.id,
            usage: { count: usage.count, limit: usage.limit, period: usage.period },
            captureUsed: Boolean(screenshot),
        });
    } catch (error) {
        await refundPlanUsage(userId, FEATURE);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Analysis service unavailable" },
            { status: 503 },
        );
    }
}
