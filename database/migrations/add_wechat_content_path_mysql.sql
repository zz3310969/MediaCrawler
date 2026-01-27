-- ============================================================================
-- 微信文章表添加 content_path 字段迁移脚本 (MySQL版本)
-- 用于支持文章内容本地文件存储优化
-- ============================================================================

-- MySQL 版本
ALTER TABLE wechat_article 
ADD COLUMN content_path VARCHAR(512) DEFAULT '' COMMENT '文章内容文件路径（本地存储）'
AFTER content;

-- 可选：为 content_path 添加索引（如果需要按路径查询）
-- CREATE INDEX idx_wechat_content_path ON wechat_article(content_path);

