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
  `created_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_templates_user_id` (`user_id`),
  CONSTRAINT `fk_user_templates_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
