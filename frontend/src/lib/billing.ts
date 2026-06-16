import { randomUUID } from "crypto";
import prisma from "@/lib/prisma";

export type PlanKey = "basic" | "plus" | "pro";
export type BillingInterval = "monthly" | "yearly";
export type TutorModality = "text" | "image" | "audio" | "video";

export type PlanEntitlements = {
    label: string;
    signalGenerationsPerMonth: number;
    signalPairs: string[];
    strategyTutor: boolean;
    tutorDocuments: number;
    tutorModalities: TutorModality[];
    backtestingDays: number;
    advancedAgents: boolean;
    priorityProcessing: boolean;
};

export type BillingSubscription = {
    id: string;
    userId: string;
    plan: PlanKey;
    status: string;
    billingInterval: BillingInterval | null;
    stripeCustomerId?: string | null;
    stripeSubscriptionId?: string | null;
    currentPeriodEnd: string | null;
    cancelAtPeriodEnd: boolean;
    createdAt: string;
    updatedAt: string;
};

const validPlans = new Set<PlanKey>(["basic", "plus", "pro"]);
const validIntervals = new Set<BillingInterval>(["monthly", "yearly"]);

export const PLAN_ENTITLEMENTS: Record<PlanKey, PlanEntitlements> = {
    basic: {
        label: "Trady Basic",
        signalGenerationsPerMonth: 2,
        signalPairs: ["EURUSD", "GBPUSD"],
        strategyTutor: false,
        tutorDocuments: 0,
        tutorModalities: [],
        backtestingDays: 0,
        advancedAgents: false,
        priorityProcessing: false,
    },
    plus: {
        label: "Trady Plus",
        signalGenerationsPerMonth: 100,
        signalPairs: ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"],
        strategyTutor: true,
        tutorDocuments: 20,
        tutorModalities: ["text", "image", "audio"],
        backtestingDays: 30,
        advancedAgents: false,
        priorityProcessing: false,
    },
    pro: {
        label: "Trady Pro",
        signalGenerationsPerMonth: 500,
        signalPairs: ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"],
        strategyTutor: true,
        tutorDocuments: 100,
        tutorModalities: ["text", "image", "audio", "video"],
        backtestingDays: 365,
        advancedAgents: true,
        priorityProcessing: true,
    },
};

export function normalizePlan(plan: unknown): PlanKey | null {
    return typeof plan === "string" && validPlans.has(plan as PlanKey) ? (plan as PlanKey) : null;
}

export function normalizeBillingInterval(interval: unknown): BillingInterval {
    return typeof interval === "string" && validIntervals.has(interval as BillingInterval)
        ? (interval as BillingInterval)
        : "monthly";
}

export function getPlanEntitlements(plan: PlanKey | null | undefined): PlanEntitlements {
    return PLAN_ENTITLEMENTS[plan ?? "basic"] ?? PLAN_ENTITLEMENTS.basic;
}

function currentPeriod() {
    const now = new Date();
    return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
}

function mapSubscription(row: BillingSubscription): BillingSubscription {
    return {
        ...row,
        plan: normalizePlan(row.plan) ?? "basic",
        cancelAtPeriodEnd: Boolean(row.cancelAtPeriodEnd),
    };
}

export async function ensureUserSubscription(userId: string): Promise<BillingSubscription> {
    const existing = await prisma.$queryRaw<BillingSubscription[]>`
        SELECT
            "id",
            "userId",
            "plan",
            "status",
            "billingInterval",
            "stripeCustomerId",
            "stripeSubscriptionId",
            "currentPeriodEnd",
            "cancelAtPeriodEnd",
            "createdAt",
            "updatedAt"
        FROM "subscription"
        WHERE "userId" = ${userId}
        LIMIT 1
    `;

    if (existing[0]) return mapSubscription(existing[0]);

    const id = randomUUID();
    await prisma.$executeRaw`
        INSERT INTO "subscription" ("id", "userId", "plan", "status", "createdAt", "updatedAt")
        VALUES (${id}, ${userId}, 'basic', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    `;

    const created = await prisma.$queryRaw<BillingSubscription[]>`
        SELECT
            "id",
            "userId",
            "plan",
            "status",
            "billingInterval",
            "stripeCustomerId",
            "stripeSubscriptionId",
            "currentPeriodEnd",
            "cancelAtPeriodEnd",
            "createdAt",
            "updatedAt"
        FROM "subscription"
        WHERE "id" = ${id}
        LIMIT 1
    `;

    return mapSubscription(created[0]);
}

export async function getUserPlan(userId: string): Promise<PlanKey> {
    const subscription = await ensureUserSubscription(userId);
    return normalizePlan(subscription.plan) ?? "basic";
}

export async function getPlanUsage(userId: string, feature: string): Promise<{ count: number; period: string }> {
    const period = currentPeriod();
    const rows = await prisma.$queryRaw<Array<{ count: number }>>`
        SELECT "count"
        FROM "planusage"
        WHERE "userId" = ${userId} AND "feature" = ${feature} AND "period" = ${period}
        LIMIT 1
    `;
    return { count: Number(rows[0]?.count ?? 0), period };
}

export async function consumePlanUsage(userId: string, feature: string, limit: number): Promise<{ count: number; limit: number; period: string; consumed: boolean }> {
    const period = currentPeriod();
    const rows = await prisma.$queryRaw<Array<{ count: number }>>`
        INSERT INTO "planusage" ("id", "userId", "feature", "period", "count", "createdAt", "updatedAt")
        VALUES (${randomUUID()}, ${userId}, ${feature}, ${period}, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT ("userId", "feature", "period")
        DO UPDATE SET
            "count" = "planusage"."count" + 1,
            "updatedAt" = CURRENT_TIMESTAMP
        WHERE "planusage"."count" < ${limit}
        RETURNING "count"
    `;

    if (!rows[0]) {
        const usage = await getPlanUsage(userId, feature);
        return { ...usage, limit, consumed: false };
    }
    return { count: Number(rows[0].count), limit, period, consumed: true };
}

export async function refundPlanUsage(userId: string, feature: string): Promise<void> {
    const period = currentPeriod();
    await prisma.$executeRaw`
        UPDATE "planusage"
        SET "count" = GREATEST("count" - 1, 0), "updatedAt" = CURRENT_TIMESTAMP
        WHERE "userId" = ${userId} AND "feature" = ${feature} AND "period" = ${period}
    `;
}

export async function setUserSubscriptionPlan(
    userId: string,
    plan: PlanKey,
    billingInterval: BillingInterval,
    stripe?: {
        stripeCustomerId?: string | null;
        stripeSubscriptionId?: string | null;
        stripePriceId?: string | null;
    }
): Promise<BillingSubscription> {
    await ensureUserSubscription(userId);

    // Postgres "currentPeriodEnd" is `timestamp without time zone`. Passing a
    // string literal made Prisma serialize it as `text` and the engine refused
    // to auto-cast (error 42804). Pass a real Date so the binding becomes a
    // proper timestamp parameter.
    const periodEnd: Date | null =
        plan === "basic"
            ? null
            : new Date(Date.now() + (billingInterval === "yearly" ? 365 : 30) * 24 * 60 * 60 * 1000);

    await prisma.$executeRaw`
        UPDATE "subscription"
        SET
            "plan" = ${plan},
            "status" = 'active',
            "billingInterval" = ${plan === "basic" ? null : billingInterval},
            "stripeCustomerId" = ${stripe?.stripeCustomerId ?? null},
            "stripeSubscriptionId" = ${stripe?.stripeSubscriptionId ?? null},
            "stripePriceId" = ${stripe?.stripePriceId ?? null},
            "currentPeriodEnd" = ${periodEnd},
            "cancelAtPeriodEnd" = false,
            "updatedAt" = CURRENT_TIMESTAMP
        WHERE "userId" = ${userId}
    `;

    return ensureUserSubscription(userId);
}
