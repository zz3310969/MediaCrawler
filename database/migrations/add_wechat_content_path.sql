-- ============================================================================
-- 微信文章表添加 content_path 字段迁移脚本
-- 用于支持文章内容本地文件存储优化
-- 
-- 说明：
--   - content_path: 存储文章HTML内容的本地文件路径
--   - 启用文件存储后，content字段将为空，内容存储在content_path指向的文件中
--   - 兼容旧数据：如果content_path为空，则从content字段读取
-- ============================================================================

-- SQLite 版本
ALTER TABLE wechat_article ADD COLUMN content_path VARCHAR(512) DEFAULT '';

-- 添加注释（SQLite不支持注释，此行仅供参考）
-- COMMENT ON COLUMN wechat_article.content_path IS '文章内容文件路径（本地存储）';

