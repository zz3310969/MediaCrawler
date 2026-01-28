-- ============================================================================
-- 微信公众号数据表迁移脚本 (MySQL版本)
-- 用于创建微信相关的数据库表
-- 
-- 表结构说明：
--   1. wechat_article       - 微信公众号文章表，存储文章基本信息和内容
--   2. wechat_comment       - 微信文章评论表，存储文章的精选评论
--   3. wechat_comment_reply - 微信评论回复表，存储评论的回复内容
--   4. wechat_account       - 微信公众号信息表，存储公众号基本资料
-- 
-- 使用方法：
--   mysql -u root -p media_crawler < add_wechat_tables_mysql.sql
-- ============================================================================

-- 设置字符集
SET NAMES utf8mb4;


-- ----------------------------------------------------------------------------
-- 微信公众号文章表
-- 存储从微信公众号采集的文章数据
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `wechat_article`;
CREATE TABLE `wechat_article` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `article_id` VARCHAR(128) NOT NULL COMMENT '文章唯一标识（通常由 fakeid + publish_time 等组合生成）',
    `title` TEXT COMMENT '文章标题',
    `link` TEXT COMMENT '文章链接地址',
    `cover` TEXT COMMENT '封面图片URL',
    `digest` TEXT COMMENT '文章摘要/简介',
    `create_time` BIGINT COMMENT '文章发布时间（Unix时间戳，秒）',
    `update_time` BIGINT COMMENT '文章更新时间（Unix时间戳，秒）',
    `author` VARCHAR(255) DEFAULT NULL COMMENT '文章作者',
    `fakeid` VARCHAR(128) DEFAULT NULL COMMENT '公众号唯一标识（用于关联公众号）',
    `account_name` VARCHAR(255) DEFAULT NULL COMMENT '公众号名称',
    `content` LONGTEXT COMMENT '文章正文内容（HTML格式）',
    `content_path` VARCHAR(512) DEFAULT '' COMMENT '文章内容文件路径（本地存储）',
    `read_num` INT UNSIGNED DEFAULT 0 COMMENT '阅读数',
    `like_num` INT UNSIGNED DEFAULT 0 COMMENT '点赞数（在看数）',
    `old_like_num` INT UNSIGNED DEFAULT 0 COMMENT '点赞数（旧版）',
    `share_num` INT UNSIGNED DEFAULT 0 COMMENT '分享数',
    `comment_count` INT UNSIGNED DEFAULT 0 COMMENT '评论数量',
    `source_keyword` VARCHAR(255) DEFAULT '' COMMENT '来源关键词（用于标记采集来源）',
    `add_ts` BIGINT COMMENT '数据入库时间（Unix时间戳，毫秒）',
    `last_modify_ts` BIGINT COMMENT '数据最后修改时间（Unix时间戳，毫秒）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_article_id` (`article_id`),
    KEY `idx_fakeid_create_time` (`fakeid`, `create_time`) COMMENT '按公众号+发布时间查询（获取某公众号文章列表）',
    KEY `idx_create_time` (`create_time`) COMMENT '按发布时间查询（时间范围筛选）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信公众号文章表';


-- ----------------------------------------------------------------------------
-- 微信文章评论表
-- 存储文章的精选评论数据
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `wechat_comment`;
CREATE TABLE `wechat_comment` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `comment_id` VARCHAR(128) NOT NULL COMMENT '评论唯一标识',
    `article_id` VARCHAR(128) DEFAULT NULL COMMENT '关联的文章ID',
    `content` TEXT COMMENT '评论内容',
    `create_time` BIGINT COMMENT '评论时间（Unix时间戳，秒）',
    `like_num` INT UNSIGNED DEFAULT 0 COMMENT '评论点赞数',
    `nick_name` VARCHAR(255) DEFAULT NULL COMMENT '评论者昵称',
    `logo_url` TEXT COMMENT '评论者头像URL',
    `add_ts` BIGINT COMMENT '数据入库时间（Unix时间戳，毫秒）',
    `last_modify_ts` BIGINT COMMENT '数据最后修改时间（Unix时间戳，毫秒）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_comment_id` (`comment_id`),
    KEY `idx_article_id` (`article_id`) COMMENT '按文章ID查询（获取某文章的所有评论）',
    KEY `idx_create_time` (`create_time`) COMMENT '按评论时间查询'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信文章评论表';


-- ----------------------------------------------------------------------------
-- 微信评论回复表
-- 存储评论的回复内容（作者回复或其他用户回复）
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `wechat_comment_reply`;
CREATE TABLE `wechat_comment_reply` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `reply_id` VARCHAR(128) NOT NULL COMMENT '回复唯一标识',
    `comment_id` VARCHAR(128) DEFAULT NULL COMMENT '关联的评论ID',
    `article_id` VARCHAR(128) DEFAULT NULL COMMENT '关联的文章ID',
    `content` TEXT COMMENT '回复内容',
    `create_time` BIGINT COMMENT '回复时间（Unix时间戳，秒）',
    `like_num` INT UNSIGNED DEFAULT 0 COMMENT '回复点赞数',
    `nick_name` VARCHAR(255) DEFAULT NULL COMMENT '回复者昵称',
    `add_ts` BIGINT COMMENT '数据入库时间（Unix时间戳，毫秒）',
    `last_modify_ts` BIGINT COMMENT '数据最后修改时间（Unix时间戳，毫秒）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_reply_id` (`reply_id`),
    KEY `idx_comment_id` (`comment_id`) COMMENT '按评论ID查询（获取某评论的所有回复）',
    KEY `idx_article_id` (`article_id`) COMMENT '按文章ID查询（获取某文章的所有回复）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信评论回复表';


-- ----------------------------------------------------------------------------
-- 微信公众号信息表
-- 存储公众号的基本资料信息
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `wechat_account`;
CREATE TABLE `wechat_account` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `fakeid` VARCHAR(128) NOT NULL COMMENT '公众号唯一标识（微信内部ID）',
    `nickname` VARCHAR(255) DEFAULT NULL COMMENT '公众号名称',
    `alias` VARCHAR(255) DEFAULT NULL COMMENT '公众号微信号（如：test_account）',
    `round_head_img` TEXT COMMENT '公众号头像URL',
    `service_type` TINYINT DEFAULT 0 COMMENT '公众号类型（0:订阅号, 1:由历史老帐号升级后的订阅号, 2:服务号）',
    `add_ts` BIGINT COMMENT '数据入库时间（Unix时间戳，毫秒）',
    `last_modify_ts` BIGINT COMMENT '数据最后修改时间（Unix时间戳，毫秒）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_fakeid` (`fakeid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微信公众号信息表';


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;

