import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

const DJANGO_API_URL = process.env.DJANGO_API_URL || "http://127.0.0.1:8000";

function getUserId(session: any): string | null {
    return session?.user?.id || null;
}

async function getCurrentMarketPrice(pair: string): Promise<number> {
    const response = await fetch(
        `${DJANGO_API_URL}/api/v2/market/candles/?pair=${encodeURIComponent(pair)}&timeframe=1h&limit=50`,
        { cache: "no-store", signal: AbortSignal.timeout(30000) },
    );
    const payload = await response.json();
    if (!response.ok || typeof payload.latest_price !== "number") {
        throw new Error("A real current market price is unavailable");
    }
    return payload.quote?.bid ?? payload.latest_price;
}

// GET all open positions for the user
export async function GET() {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const positions = await prisma.position.findMany({
        where: { userId, status: "OPEN" },
        orderBy: { openedAt: "desc" },
    });
    return NextResponse.json(positions);
}

// POST create a new position (BUY/SELL)
export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { analysisId, size, stopLoss, takeProfit } = await req.json();

    if (!analysisId || !size) {
        return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const analysis = await prisma.marketAnalysis.findFirst({
        where: { id: analysisId, userId },
    });
    if (!analysis || !["BUY", "SELL"].includes(analysis.action)) {
        return NextResponse.json({ error: "A current approved analysis is required" }, { status: 400 });
    }

    const position = await prisma.position.create({
        data: {
            userId,
            analysisId: analysis.id,
            pair: analysis.pair,
            side: analysis.action,
            size: Number(size),
            entryPrice: analysis.latestPrice,
            currentPrice: analysis.latestPrice,
            stopLoss: stopLoss || null,
            takeProfit: takeProfit || null,
        },
    });

    return NextResponse.json(position, { status: 201 });
}

// PATCH close a position
export async function PATCH(req: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { id } = await req.json();

    const position = await prisma.position.findFirst({
        where: { id, userId, status: "OPEN" },
    });

    if (!position) {
        return NextResponse.json({ error: "Position not found" }, { status: 404 });
    }

    let currentPrice: number;
    try {
        currentPrice = await getCurrentMarketPrice(position.pair);
    } catch (error) {
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Market price unavailable" },
            { status: 503 },
        );
    }

    const signedMove = position.side === "BUY"
        ? currentPrice - position.entryPrice
        : position.entryPrice - currentPrice;
    const pnl = position.side === "BUY"
        ? (currentPrice - position.entryPrice) * position.size * 100000
        : (position.entryPrice - currentPrice) * position.size * 100000;
    const pnlPct = (signedMove / position.entryPrice) * 100;

    const updated = await prisma.position.update({
        where: { id },
        data: {
            status: "CLOSED",
            currentPrice,
            pnl: Math.round(pnl * 100) / 100,
            pnlPct: Math.round(pnlPct * 100) / 100,
            closedAt: new Date(),
        },
    });

    return NextResponse.json(updated);
}

