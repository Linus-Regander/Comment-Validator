CREATE TABLE IF NOT EXISTS comments (
    id         VARCHAR(36) NOT NULL,
    content    TEXT        NOT NULL,
    tenant_id  VARCHAR(36) NOT NULL,
    object_id  VARCHAR(36) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    INDEX ix_comments_owner (tenant_id, object_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;