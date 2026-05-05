-- CreateTable
CREATE TABLE `KycVerification` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `userId` VARCHAR(191) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `fullName` VARCHAR(120) NULL,
    `cinNumber` VARCHAR(40) NULL,
    `nationality` VARCHAR(60) NULL,
    `ocrText` TEXT NULL,
    `confidenceBasic` DOUBLE NULL,
    `extractedFields` JSON NULL,
    `uploadedAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `confirmedAt` DATETIME(3) NULL,

    INDEX `KycVerification_userId_idx`(`userId`),
    INDEX `KycVerification_status_idx`(`status`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `KycVerification` ADD CONSTRAINT `KycVerification_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `User`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
