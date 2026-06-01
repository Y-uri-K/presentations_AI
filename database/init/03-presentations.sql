USE `presentations_ai`;

CREATE TABLE IF NOT EXISTS `presentations` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`         BIGINT UNSIGNED NOT NULL,
  `template_id`     BIGINT UNSIGNED NULL,
  `agent_id`        VARCHAR(32)     NOT NULL,
  `title`           VARCHAR(255)    NOT NULL DEFAULT 'Презентация',
  `prompt`          TEXT            NULL,
  `outline`         MEDIUMTEXT      NOT NULL,
  `slides_json`     JSON            NULL,
  `status`          ENUM('draft', 'building', 'ready', 'failed') NOT NULL DEFAULT 'draft',
  `build_stage`     VARCHAR(64)     NULL,
  `error_message`   TEXT            NULL,
  `pptx_data`       LONGBLOB        NULL,
  `source_filenames` JSON           NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_presentations_user_id` (`user_id`),
  KEY `idx_presentations_status` (`status`),
  CONSTRAINT `fk_presentations_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_presentations_template`
    FOREIGN KEY (`template_id`) REFERENCES `user_templates` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `presentation_source_files` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `presentation_id`   BIGINT UNSIGNED NOT NULL,
  `filename`          VARCHAR(255)    NOT NULL,
  `content`           LONGBLOB        NOT NULL,
  `created_at`        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_presentation_sources_presentation_id` (`presentation_id`),
  CONSTRAINT `fk_presentation_sources_presentation`
    FOREIGN KEY (`presentation_id`) REFERENCES `presentations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
