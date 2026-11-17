-- P3 阅读记录表：支持「继续阅读」跨设备同步
-- 日期：2026-11-17
-- 说明：SQLite 由 Base.metadata.create_all 自动建表；此文件供已有数据库手工迁移

CREATE TABLE IF NOT EXISTS note_views (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    note_id VARCHAR(36) NOT NULL,
    viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_note_views_user_note UNIQUE (user_id, note_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_note_views_user_time
    ON note_views (user_id, viewed_at DESC);
