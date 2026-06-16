CREATE TABLE "subscription" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "plan" TEXT NOT NULL DEFAULT 'basic',
    "status" TEXT NOT NULL DEFAULT 'active',
    "billingInterval" TEXT,
    "stripeCustomerId" TEXT,
    "stripeSubscriptionId" TEXT,
    "stripePriceId" TEXT,
    "currentPeriodEnd" DATETIME,
    "cancelAtPeriodEnd" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "subscription_userId_fkey" FOREIGN KEY ("userId") REFERENCES "user" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE UNIQUE INDEX "subscription_userId_key" ON "subscription"("userId");
CREATE INDEX "subscription_plan_idx" ON "subscription"("plan");
CREATE INDEX "subscription_status_idx" ON "subscription"("status");

INSERT INTO "subscription" ("id", "userId", "plan", "status")
SELECT lower(hex(randomblob(16))), "id", 'basic', 'active'
FROM "user"
WHERE NOT EXISTS (
    SELECT 1 FROM "subscription" WHERE "subscription"."userId" = "user"."id"
);
