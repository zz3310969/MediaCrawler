-- 微信公众号数据表迁移脚本
-- 用于创建微信相关的数据库表

-- 微信公众号文章表
CREATE TABLE IF NOT EXISTS wechat_article (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id VARCHAR(128) NOT NULL UNIQUE,
    title TEXT,
    link TEXT,
    cover TEXT,
    digest TEXT,
    create_time BIGINT,
    update_time BIGINT,
    author VARCHAR(255),
    fakeid VARCHAR(128),
    account_name VARCHAR(255),
    content TEXT,
    read_num INTEGER DEFAULT 0,
    like_num INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    source_keyword VARCHAR(255) DEFAULT '',
    add_ts BIGINT,
    last_modify_ts BIGINT
);

CREATE INDEX IF NOT EXISTS idx_wechat_article_id ON wechat_article(article_id);
CREATE INDEX IF NOT EXISTS idx_wechat_fakeid_create_time ON wechat_article(fakeid, create_time);
CREATE INDEX IF NOT EXISTS idx_wechat_create_time ON wechat_article(create_time);

-- 微信文章评论表
CREATE TABLE IF NOT EXISTS wechat_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id VARCHAR(128) NOT NULL UNIQUE,
    article_id VARCHAR(128),
    content TEXT,
    create_time BIGINT,
    like_num INTEGER DEFAULT 0,
    nick_name VARCHAR(255),
    logo_url TEXT,
    add_ts BIGINT,
    last_modify_ts BIGINT
);

CREATE INDEX IF NOT EXISTS idx_wechat_comment_id ON wechat_comment(comment_id);
CREATE INDEX IF NOT EXISTS idx_wechat_comment_article_id ON wechat_comment(article_id);
CREATE INDEX IF NOT EXISTS idx_wechat_comment_create_time ON wechat_comment(create_time);

-- 微信评论回复表
CREATE TABLE IF NOT EXISTS wechat_comment_reply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_id VARCHAR(128) NOT NULL UNIQUE,
    comment_id VARCHAR(128),
    article_id VARCHAR(128),
    content TEXT,
    create_time BIGINT,
    like_num INTEGER DEFAULT 0,
    nick_name VARCHAR(255),
    add_ts BIGINT,
    last_modify_ts BIGINT
);

CREATE INDEX IF NOT EXISTS idx_wechat_reply_id ON wechat_comment_reply(reply_id);
CREATE INDEX IF NOT EXISTS idx_wechat_reply_comment_id ON wechat_comment_reply(comment_id);
CREATE INDEX IF NOT EXISTS idx_wechat_reply_article_id ON wechat_comment_reply(article_id);

-- 微信公众号信息表
CREATE TABLE IF NOT EXISTS wechat_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fakeid VARCHAR(128) NOT NULL UNIQUE,
    nickname VARCHAR(255),
    alias VARCHAR(255),
    round_head_img TEXT,
    service_type INTEGER DEFAULT 0,
    add_ts BIGINT,
    last_modify_ts BIGINT
);

CREATE INDEX IF NOT EXISTS idx_wechat_account_fakeid ON wechat_account(fakeid);
