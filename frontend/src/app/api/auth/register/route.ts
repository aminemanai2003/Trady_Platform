import { NextRequest, NextResponse } from "next/server";
import { hash } from "bcryptjs";
import prisma from "@/lib/prisma";

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

        // Create default risk / notification settings row
        await prisma.userSettings.create({ data: { userId: user.id } });

        // Persist KYC OCR data when the user confirmed it during registration
        if (kyc?.confirmed) {
            try {
                await prisma.kycVerification.create({
                    data: {
                        userId:          user.id,
                        status:          "pending",
                        fullName:        kyc.fullName        || null,
                        cinNumber:       kyc.cinNumber       || null,
                        nationality:     kyc.nationality     || null,
                        documentCountry: kyc.documentCountry || null,
                        documentType:    kyc.documentType    || null,
                        dateOfBirth:     kyc.dateOfBirth     || null,
                        expirationDate:  kyc.expirationDate  || null,
                        confidenceBasic: typeof kyc.confidenceBasic === "number" ? kyc.confidenceBasic : null,
                        ocrText:         kyc.ocrText         || null,
                        confirmedAt:     new Date(),
                    },
                });
            } catch (kycError) {
                // Non-fatal — registration succeeds even if KYC persistence fails
                console.warn("KYC persistence skipped:", kycError);
            }
        }

        return NextResponse.json({ id: user.id, email: user.email }, { status: 201 });
    } catch (error) {
        console.error("Registration error:", error);
        return NextResponse.json({ error: "Registration failed" }, { status: 500 });
    }
}

