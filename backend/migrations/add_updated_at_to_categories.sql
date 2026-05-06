-- 为 categories 和 content_types 表添加 updated_at 列
-- 创建时间: 2026-05-07

ALTER TABLE categories ADD COLUMN updated_at DATETIME;

ALTER TABLE content_types ADD COLUMN updated_at DATETIME;
