CREATE DATABASE IF NOT EXISTS `presentations_ai`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `presentations_ai`;

CREATE TABLE IF NOT EXISTS `users` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username`        VARCHAR(64)     NOT NULL,
  `email`           VARCHAR(255)    NOT NULL,
  `password_hash`   VARCHAR(255)    NOT NULL,
  `profile_image`   LONGTEXT        NULL,
  `email_verified`  TINYINT(1)      NOT NULL DEFAULT 0,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `pending_registrations` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username`        VARCHAR(64)     NOT NULL,
  `email`           VARCHAR(255)    NOT NULL,
  `password_hash`   VARCHAR(255)    NOT NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at`      TIMESTAMP       NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pending_registrations_email` (`email`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `verification_codes` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `email`           VARCHAR(255)    NOT NULL,
  `code_hash`       VARCHAR(255)    NOT NULL,
  `purpose`         VARCHAR(32)     NOT NULL DEFAULT 'register',
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at`      TIMESTAMP       NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_verification_codes_email_purpose` (`email`, `purpose`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
