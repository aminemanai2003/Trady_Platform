/*
  Warnings:

  - You are about to drop the column `extractedFields` on the `kycverification` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE `kycverification` DROP COLUMN `extractedFields`,
    ADD COLUMN `dateOfBirth` VARCHAR(20) NULL,
    ADD COLUMN `documentCountry` VARCHAR(60) NULL,
    ADD COLUMN `documentType` VARCHAR(40) NULL,
    ADD COLUMN `expirationDate` VARCHAR(20) NULL;

-- CreateTable
CREATE TABLE `user` (
    `id` VARCHAR(191) NOT NULL,
    `name` VARCHAR(191) NULL,
    `email` VARCHAR(191) NOT NULL,
    `hashedPassword` VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `updatedAt` DATETIME(3) NOT NULL,

    UNIQUE INDEX `user_email_key`(`email`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `position` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `userId` VARCHAR(191) NOT NULL,
    `pair` VARCHAR(10) NOT NULL,
    `side` VARCHAR(4) NOT NULL,
    `size` DOUBLE NOT NULL,
    `entryPrice` DOUBLE NOT NULL,
    `currentPrice` DOUBLE NOT NULL,
    `stopLoss` DOUBLE NULL,
    `takeProfit` DOUBLE NULL,
    `pnl` DOUBLE NOT NULL DEFAULT 0,
    `pnlPct` DOUBLE NOT NULL DEFAULT 0,
    `status` VARCHAR(10) NOT NULL DEFAULT 'OPEN',
    `openedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `closedAt` DATETIME(3) NULL,

    INDEX `position_userId_idx`(`userId`),
    INDEX `position_userId_status_idx`(`userId`, `status`),
    INDEX `position_pair_idx`(`pair`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `usersettings` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `userId` VARCHAR(191) NOT NULL,
    `maxPositionSize` DOUBLE NOT NULL DEFAULT 0.5,
    `maxDailyLoss` DOUBLE NOT NULL DEFAULT 500,
    `maxDrawdown` DOUBLE NOT NULL DEFAULT 15,
    `maxOpenPositions` INTEGER NOT NULL DEFAULT 4,
    `minConsensus` INTEGER NOT NULL DEFAULT 2,
    `minConfidence` DOUBLE NOT NULL DEFAULT 60,
    `defaultStopLoss` DOUBLE NOT NULL DEFAULT 40,
    `defaultTakeProfit` DOUBLE NOT NULL DEFAULT 80,
    `trailingStop` BOOLEAN NOT NULL DEFAULT false,
    `notifySignals` BOOLEAN NOT NULL DEFAULT true,
    `notifyHighConfidence` BOOLEAN NOT NULL DEFAULT true,
    `notifyAgentOffline` BOOLEAN NOT NULL DEFAULT true,
    `notifyDrawdown` BOOLEAN NOT NULL DEFAULT true,
    `notifyDailySummary` BOOLEAN NOT NULL DEFAULT false,
    `notifyCalendar` BOOLEAN NOT NULL DEFAULT true,

    UNIQUE INDEX `usersettings_userId_key`(`userId`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `signal` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `pair` VARCHAR(10) NOT NULL,
    `direction` VARCHAR(10) NOT NULL,
    `confidence` DOUBLE NOT NULL,
    `macroScore` DOUBLE NULL,
    `technicalScore` DOUBLE NULL,
    `sentimentScore` DOUBLE NULL,
    `consensusCount` INTEGER NOT NULL DEFAULT 0,
    `rationale` TEXT NULL,
    `entryPrice` DOUBLE NULL,
    `stopLoss` DOUBLE NULL,
    `takeProfit` DOUBLE NULL,
    `isActive` BOOLEAN NOT NULL DEFAULT true,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `order` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `userId` VARCHAR(191) NOT NULL,
    `pair` VARCHAR(10) NOT NULL,
    `side` VARCHAR(4) NOT NULL,
    `type` VARCHAR(10) NOT NULL,
    `size` DOUBLE NOT NULL,
    `price` DOUBLE NULL,
    `stopLoss` DOUBLE NULL,
    `takeProfit` DOUBLE NULL,
    `status` VARCHAR(10) NOT NULL DEFAULT 'PENDING',
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `kycverification` ADD CONSTRAINT `kycverification_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `user`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `position` ADD CONSTRAINT `position_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `user`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `usersettings` ADD CONSTRAINT `usersettings_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `user`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- RenameIndex
ALTER TABLE `kycverification` RENAME INDEX `KycVerification_status_idx` TO `kycverification_status_idx`;

-- RenameIndex
ALTER TABLE `kycverification` RENAME INDEX `KycVerification_userId_idx` TO `kycverification_userId_idx`;
