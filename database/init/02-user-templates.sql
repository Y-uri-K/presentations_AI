USE `presentations_ai`;

CREATE TABLE IF NOT EXISTS `user_templates` (
  `id`                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`             BIGINT UNSIGNED NOT NULL,
  `name`                VARCHAR(255)    NOT NULL,
  `original_filename`   VARCHAR(255)    NOT NULL,
  `file_type`           ENUM('pptx', 'pdf') NOT NULL,
  `mime_type`           VARCHAR(128)    NOT NULL,
  `size_bytes`          BIGINT UNSIGNED NOT NULL,
  `file_data`           LONGBLOB        NOT NULL,
  `is_public`           TINYINT(1)      NOT NULL DEFAULT 0,
  `download_count`      BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `created_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_templates_user_id` (`user_id`),
  KEY `idx_user_templates_public_downloads` (`is_public`, `download_count`),
  KEY `idx_user_templates_public_created` (`is_public`, `created_at`),
  CONSTRAINT `fk_user_templates_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `template_ratings` (
  `id`                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `template_id`         BIGINT UNSIGNED NOT NULL,
  `user_id`             BIGINT UNSIGNED NOT NULL,
  `rating`              TINYINT UNSIGNED NOT NULL,
  `created_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_template_ratings_template_user` (`template_id`, `user_id`),
  KEY `idx_template_ratings_template_id` (`template_id`),
  KEY `idx_template_ratings_user_id` (`user_id`),
  CONSTRAINT `fk_template_ratings_template`
    FOREIGN KEY (`template_id`) REFERENCES `user_templates` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_template_ratings_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_template_ratings_rating`
    CHECK (`rating` BETWEEN 1 AND 5)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
