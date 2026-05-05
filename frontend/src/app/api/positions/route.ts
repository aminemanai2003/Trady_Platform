import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

function getUserId(session: any): string | null {
    return session?.user?.id || null;
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

    const { pair, side, size, entryPrice, stopLoss, takeProfit } = await req.json();

    if (!pair || !side || !size || !entryPrice) {
        return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const position = await prisma.position.create({
        data: {
            userId,
            pair,
            side,
            size,
            entryPrice,
            currentPrice: entryPrice,
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

    const { id, currentPrice } = await req.json();

    const position = await prisma.position.findFirst({
        where: { id, userId, status: "OPEN" },
    });

    if (!position) {
        return NextResponse.json({ error: "Position not found" }, { status: 404 });
    }

    const pnl = position.side === "BUY"
        ? (currentPrice - position.entryPrice) * position.size * 100000
        : (position.entryPrice - currentPrice) * position.size * 100000;

    const pnlPct = ((currentPrice - position.entryPrice) / position.entryPrice) * 100;

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

