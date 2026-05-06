import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

function getUserId(session: { user?: { id?: string } } | null): string | null {
    return session?.user?.id || null;
}

export async function GET() {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    let settings = await prisma.userSettings.findUnique({ where: { userId } });
    if (!settings) {
        settings = await prisma.userSettings.create({ data: { userId } });
    }
    return NextResponse.json(settings);
}

export async function PUT(req: NextRequest) {
    const session = await getServerSession(authOptions);
    const userId = getUserId(session);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const data = await req.json();
    delete data.id;
    delete data.userId;

    const settings = await prisma.userSettings.upsert({
        where: { userId },
        update: data,
        create: { userId, ...data },
    });

    return NextResponse.json(settings);
}
