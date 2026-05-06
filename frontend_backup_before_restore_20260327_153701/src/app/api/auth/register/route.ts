import { NextRequest, NextResponse } from "next/server";
import { hash } from "bcryptjs";
import prisma from "@/lib/prisma";

export async function POST(req: NextRequest) {
    try {
        const { name, email, password } = await req.json();

        if (!email || !password) {
            return NextResponse.json({ error: "Email and password required" }, { status: 400 });
        }

        const exists = await prisma.user.findUnique({ where: { email } });
        if (exists) {
            return NextResponse.json({ error: "Account already exists" }, { status: 409 });
        }

        const hashedPassword = await hash(password, 12);
        const user = await prisma.user.create({
            data: { name: name || email.split("@")[0], email, hashedPassword },
        });

        // Create default settings
        await prisma.userSettings.create({ data: { userId: user.id } });

        return NextResponse.json({ id: user.id, email: user.email }, { status: 201 });
    } catch (error) {
        console.error("Registration error:", error);
        return NextResponse.json({ error: "Registration failed" }, { status: 500 });
    }
}
