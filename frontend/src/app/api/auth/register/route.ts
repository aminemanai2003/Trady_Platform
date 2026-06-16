import { NextRequest, NextResponse } from "next/server";
import { hash } from "bcryptjs";
import { mkdir, writeFile } from "fs/promises";
import path from "path";
import prisma from "@/lib/prisma";
import { ensureUserSubscription } from "@/lib/billing";

export const runtime = "nodejs";

type RegisterPayload = {
    name: string;
    email: string;
    password: string;
    phoneNumber: string;
    country: string;
    city: string;
    address: string;
    profession: string;
    tradingExperience: string;
    preferredMarket: string;
    bio: string;
    kyc?: Record<string, unknown>;
    profilePicture?: File | null;
};

function clean(value: unknown): string {
    return typeof value === "string" ? value.trim() : "";
}

function safeJson(value: FormDataEntryValue | null): Record<string, unknown> | undefined {
    if (typeof value !== "string" || !value.trim()) return undefined;
    try {
        const parsed = JSON.parse(value);
        return parsed && typeof parsed === "object" ? parsed as Record<string, unknown> : undefined;
    } catch {
        return undefined;
    }
}

async function readPayload(req: NextRequest): Promise<RegisterPayload> {
    const contentType = req.headers.get("content-type") || "";

    if (contentType.includes("multipart/form-data")) {
        const form = await req.formData();
        const file = form.get("profilePicture");
        return {
            name: clean(form.get("name")),
            email: clean(form.get("email")).toLowerCase(),
            password: clean(form.get("password")),
            phoneNumber: clean(form.get("phoneNumber")),
            country: clean(form.get("country")),
            city: clean(form.get("city")),
            address: clean(form.get("address")),
            profession: clean(form.get("profession")),
            tradingExperience: clean(form.get("tradingExperience")),
            preferredMarket: clean(form.get("preferredMarket")),
            bio: clean(form.get("bio")),
            kyc: safeJson(form.get("kyc")),
            profilePicture: file instanceof File && file.size > 0 ? file : null,
        };
    }

    const body = await req.json();
    return {
        name: clean(body.name),
        email: clean(body.email).toLowerCase(),
        password: clean(body.password),
        phoneNumber: clean(body.phoneNumber),
        country: clean(body.country),
        city: clean(body.city),
        address: clean(body.address),
        profession: clean(body.profession),
        tradingExperience: clean(body.tradingExperience),
        preferredMarket: clean(body.preferredMarket),
        bio: clean(body.bio),
        kyc: body.kyc,
        profilePicture: null,
    };
}

async function saveProfilePicture(userId: string, file: File | null | undefined): Promise<string | null> {
    if (!file) return null;
    if (!file.type.startsWith("image/")) {
        throw new Error("Profile picture must be an image.");
    }
    if (file.size > 5 * 1024 * 1024) {
        throw new Error("Profile picture must be 5 MB or smaller.");
    }

    const ext = file.type.includes("png") ? "png" : file.type.includes("webp") ? "webp" : "jpg";
    const dir = path.join(process.cwd(), "public", "uploads", "avatars");
    const filename = `${userId}-${Date.now()}.${ext}`;
    await mkdir(dir, { recursive: true });
    await writeFile(path.join(dir, filename), Buffer.from(await file.arrayBuffer()));
    return `/uploads/avatars/${filename}`;
}

export async function POST(req: NextRequest) {
    try {
        const {
            name,
            email,
            password,
            phoneNumber,
            country,
            city,
            address,
            profession,
            tradingExperience,
            preferredMarket,
            bio,
            kyc,
            profilePicture,
        } = await readPayload(req);

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

        const image = await saveProfilePicture(user.id, profilePicture);
        await prisma.$executeRaw`
            UPDATE "user"
            SET
                "image" = ${image},
                "phoneNumber" = ${phoneNumber || null},
                "country" = ${country || null},
                "city" = ${city || null},
                "address" = ${address || null},
                "profession" = ${profession || null},
                "tradingExperience" = ${tradingExperience || null},
                "preferredMarket" = ${preferredMarket || null},
                "bio" = ${bio || null}
            WHERE "id" = ${user.id}
        `;

        await prisma.userSettings.upsert({
            where: { userId: user.id },
            update: {},
            create: { userId: user.id },
        });
        await ensureUserSubscription(user.id);

        if (kyc?.confirmed) {
            try {
                await prisma.kycVerification.create({
                    data: {
                        userId:          user.id,
                        status:          "pending",
                        fullName:        clean(kyc.fullName)        || null,
                        cinNumber:       clean(kyc.cinNumber)       || null,
                        nationality:     clean(kyc.nationality)     || null,
                        documentCountry: clean(kyc.documentCountry) || null,
                        documentType:    clean(kyc.documentType)    || null,
                        dateOfBirth:     clean(kyc.dateOfBirth)     || null,
                        expirationDate:  clean(kyc.expirationDate)  || null,
                        confidenceBasic: typeof kyc.confidenceBasic === "number" ? kyc.confidenceBasic : null,
                        ocrText:         clean(kyc.ocrText)         || null,
                        confirmedAt:     new Date(),
                    },
                });
            } catch (kycError) {
                console.warn("KYC persistence skipped:", kycError);
            }
        }

        return NextResponse.json({ id: user.id, email: user.email, image }, { status: 201 });
    } catch (error) {
        console.error("Registration error:", error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Registration failed" },
            { status: 500 }
        );
    }
}
