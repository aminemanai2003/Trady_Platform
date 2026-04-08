import { NextRequest, NextResponse } from "next/server";
import { hash } from "bcryptjs";
import prisma from "@/lib/prisma";

type KycCreatePayload = {
    userId: string;
    status: string;
    fullName: string | null;
    cinNumber: string | null;
    nationality: string | null;
    confidenceBasic: number | null;
    ocrText: string | null;
    extractedFields: {
        fullName: string | null;
        cinNumber: string | null;
        nationality: string | null;
        documentCountry: string | null;
        documentType: string | null;
        dateOfBirth: string | null;
        expirationDate: string | null;
    };
    confirmedAt: Date;
};

type PrismaWithOptionalKyc = {
    kycVerification?: {
        create: (args: { data: KycCreatePayload }) => Promise<unknown>;
    };
};

export async function POST(req: NextRequest) {
    try {
        const { name, email, password, kyc } = await req.json();

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

        // Persist lightweight KYC OCR step (user-confirmed values only)
        if (kyc?.confirmed) {
            try {
                const prismaKyc = prisma as unknown as PrismaWithOptionalKyc;
                if (!prismaKyc.kycVerification) {
                    throw new Error("kycVerification model unavailable");
                }

                await prismaKyc.kycVerification.create({
                    data: {
                        userId: user.id,
                        status: "pending",
                        fullName: kyc.fullName || null,
                        cinNumber: kyc.cinNumber || null,
                        nationality: kyc.nationality || null,
                        confidenceBasic: typeof kyc.confidenceBasic === "number" ? kyc.confidenceBasic : null,
                        ocrText: kyc.ocrText || null,
                        extractedFields: {
                            fullName: kyc.fullName || null,
                            cinNumber: kyc.cinNumber || null,
                            nationality: kyc.nationality || null,
                            documentCountry: kyc.documentCountry || null,
                            documentType: kyc.documentType || null,
                            dateOfBirth: kyc.dateOfBirth || null,
                            expirationDate: kyc.expirationDate || null,
                        },
                        confirmedAt: new Date(),
                    },
                });
            } catch (kycError) {
                // Keep registration resilient if KYC table is not migrated yet.
                console.warn("KYC persistence skipped:", kycError);
            }
        }

        return NextResponse.json({ id: user.id, email: user.email }, { status: 201 });
    } catch (error) {
        console.error("Registration error:", error);
        return NextResponse.json({ error: "Registration failed" }, { status: 500 });
    }
}

