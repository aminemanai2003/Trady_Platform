CREATE TABLE "marketanalysis" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "pair" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL,
    "horizon" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "marketTimestamp" TIMESTAMP(3) NOT NULL,
    "dataSource" TEXT NOT NULL,
    "dataStatus" TEXT NOT NULL,
    "latestPrice" DOUBLE PRECISION NOT NULL,
    "screenshotHash" TEXT,
    "result" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "marketanalysis_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "position" ADD COLUMN "analysisId" TEXT;

CREATE INDEX "marketanalysis_userId_createdAt_idx" ON "marketanalysis"("userId", "createdAt");
CREATE INDEX "marketanalysis_pair_timeframe_idx" ON "marketanalysis"("pair", "timeframe");
CREATE INDEX "position_analysisId_idx" ON "position"("analysisId");

ALTER TABLE "marketanalysis"
ADD CONSTRAINT "marketanalysis_userId_fkey"
FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "position"
ADD CONSTRAINT "position_analysisId_fkey"
FOREIGN KEY ("analysisId") REFERENCES "marketanalysis"("id") ON DELETE SET NULL ON UPDATE CASCADE;
