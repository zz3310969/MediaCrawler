-- ============================================================================
-- 微信公众号文章表 - 添加缺失的列
-- 用于修复已存在的表结构
-- ============================================================================

-- MySQL 版本
-- ALTER TABLE wechat_article ADD COLUMN old_like_num INT UNSIGNED DEFAULT 0 COMMENT '点赞数（旧版）' AFTER like_num;
-- ALTER TABLE wechat_article ADD COLUMN share_num INT UNSIGNED DEFAULT 0 COMMENT '分享数' AFTER old_like_num;

-- SQLite 版本
-- ALTER TABLE wechat_article ADD COLUMN old_like_num INTEGER DEFAULT 0;
-- ALTER TABLE wechat_article ADD COLUMN share_num INTEGER DEFAULT 0;

-- ============================================================================
-- 使用方法 (MySQL):
--   mysql -u root -p media_crawler -e "ALTER TABLE wechat_article ADD COLUMN old_like_num INT UNSIGNED DEFAULT 0 COMMENT '点赞数（旧版）' AFTER like_num;"
--   mysql -u root -p media_crawler -e "ALTER TABLE wechat_article ADD COLUMN share_num INT UNSIGNED DEFAULT 0 COMMENT '分享数' AFTER old_like_num;"
--
-- 或者使用 Python 脚本执行
-- ============================================================================
