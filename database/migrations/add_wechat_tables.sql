-- ============================================================================
-- 微信公众号数据表迁移脚本
-- 用于创建微信相关的数据库表
-- 
-- 表结构说明：
--   1. wechat_article       - 微信公众号文章表，存储文章基本信息和内容
--   2. wechat_comment       - 微信文章评论表，存储文章的精选评论
--   3. wechat_comment_reply - 微信评论回复表，存储评论的回复内容
--   4. wechat_account       - 微信公众号信息表，存储公众号基本资料
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 微信公众号文章表
-- 存储从微信公众号采集的文章数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wechat_article (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
    article_id VARCHAR(128) NOT NULL UNIQUE,        -- 文章唯一标识（通常由 fakeid + publish_time 等组合生成）
    title TEXT,                                     -- 文章标题
    link TEXT,                                      -- 文章链接地址
    cover TEXT,                                     -- 封面图片URL
    digest TEXT,                                    -- 文章摘要/简介
    create_time BIGINT,                             -- 文章发布时间（Unix时间戳，秒）
    update_time BIGINT,                             -- 文章更新时间（Unix时间戳，秒）
    author VARCHAR(255),                            -- 文章作者
    fakeid VARCHAR(128),                            -- 公众号唯一标识（用于关联公众号）
    account_name VARCHAR(255),                      -- 公众号名称
    content TEXT,                                   -- 文章正文内容（HTML格式）
    read_num INTEGER DEFAULT 0,                     -- 阅读数
    like_num INTEGER DEFAULT 0,                     -- 点赞数（在看数）
    old_like_num INTEGER DEFAULT 0,                 -- 点赞数（旧版）
    share_num INTEGER DEFAULT 0,                    -- 分享数
    comment_count INTEGER DEFAULT 0,                -- 评论数量
    source_keyword VARCHAR(255) DEFAULT '',         -- 来源关键词（用于标记采集来源）
    add_ts BIGINT,                                  -- 数据入库时间（Unix时间戳，毫秒）
    last_modify_ts BIGINT                           -- 数据最后修改时间（Unix时间戳，毫秒）
);

-- 文章表索引
CREATE INDEX IF NOT EXISTS idx_wechat_article_id ON wechat_article(article_id);                     -- 按文章ID查询
CREATE INDEX IF NOT EXISTS idx_wechat_fakeid_create_time ON wechat_article(fakeid, create_time);    -- 按公众号+发布时间查询（获取某公众号文章列表）
CREATE INDEX IF NOT EXISTS idx_wechat_create_time ON wechat_article(create_time);                   -- 按发布时间查询（时间范围筛选）


-- ----------------------------------------------------------------------------
-- 微信文章评论表
-- 存储文章的精选评论数据
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wechat_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
    comment_id VARCHAR(128) NOT NULL UNIQUE,        -- 评论唯一标识
    article_id VARCHAR(128),                        -- 关联的文章ID
    content TEXT,                                   -- 评论内容
    create_time BIGINT,                             -- 评论时间（Unix时间戳，秒）
    like_num INTEGER DEFAULT 0,                     -- 评论点赞数
    nick_name VARCHAR(255),                         -- 评论者昵称
    logo_url TEXT,                                  -- 评论者头像URL
    add_ts BIGINT,                                  -- 数据入库时间（Unix时间戳，毫秒）
    last_modify_ts BIGINT                           -- 数据最后修改时间（Unix时间戳，毫秒）
);

-- 评论表索引
CREATE INDEX IF NOT EXISTS idx_wechat_comment_id ON wechat_comment(comment_id);                     -- 按评论ID查询
CREATE INDEX IF NOT EXISTS idx_wechat_comment_article_id ON wechat_comment(article_id);             -- 按文章ID查询（获取某文章的所有评论）
CREATE INDEX IF NOT EXISTS idx_wechat_comment_create_time ON wechat_comment(create_time);           -- 按评论时间查询


-- ----------------------------------------------------------------------------
-- 微信评论回复表
-- 存储评论的回复内容（作者回复或其他用户回复）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wechat_comment_reply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
    reply_id VARCHAR(128) NOT NULL UNIQUE,          -- 回复唯一标识
    comment_id VARCHAR(128),                        -- 关联的评论ID
    article_id VARCHAR(128),                        -- 关联的文章ID
    content TEXT,                                   -- 回复内容
    create_time BIGINT,                             -- 回复时间（Unix时间戳，秒）
    like_num INTEGER DEFAULT 0,                     -- 回复点赞数
    nick_name VARCHAR(255),                         -- 回复者昵称
    add_ts BIGINT,                                  -- 数据入库时间（Unix时间戳，毫秒）
    last_modify_ts BIGINT                           -- 数据最后修改时间（Unix时间戳，毫秒）
);

-- 评论回复表索引
CREATE INDEX IF NOT EXISTS idx_wechat_reply_id ON wechat_comment_reply(reply_id);                   -- 按回复ID查询
CREATE INDEX IF NOT EXISTS idx_wechat_reply_comment_id ON wechat_comment_reply(comment_id);         -- 按评论ID查询（获取某评论的所有回复）
CREATE INDEX IF NOT EXISTS idx_wechat_reply_article_id ON wechat_comment_reply(article_id);         -- 按文章ID查询（获取某文章的所有回复）


-- ----------------------------------------------------------------------------
-- 微信公众号信息表
-- 存储公众号的基本资料信息
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wechat_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
    fakeid VARCHAR(128) NOT NULL UNIQUE,            -- 公众号唯一标识（微信内部ID）
    nickname VARCHAR(255),                          -- 公众号名称
    alias VARCHAR(255),                             -- 公众号微信号（如：test_account）
    round_head_img TEXT,                            -- 公众号头像URL
    service_type INTEGER DEFAULT 0,                 -- 公众号类型（0:订阅号, 1:由历史老帐号升级后的订阅号, 2:服务号）
    add_ts BIGINT,                                  -- 数据入库时间（Unix时间戳，毫秒）
    last_modify_ts BIGINT                           -- 数据最后修改时间（Unix时间戳，毫秒）
);

-- 公众号信息表索引
CREATE INDEX IF NOT EXISTS idx_wechat_account_fakeid ON wechat_account(fakeid);                     -- 按公众号ID查询
