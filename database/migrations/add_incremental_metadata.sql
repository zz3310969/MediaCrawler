-- 数据库迁移脚本：添加增量爬取元数据表
-- 创建时间: 2026-01-26
-- 说明: 为MediaCrawler项目添加增量爬取功能所需的元数据表

-- 创建增量元数据表
CREATE TABLE IF NOT EXISTS incremental_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform VARCHAR(64) NOT NULL,                -- 平台: xhs, dy, wb等
    crawler_type VARCHAR(64) NOT NULL,            -- 类型: search, creator, detail
    
    -- 目标标识
    target_key VARCHAR(255) NOT NULL,             -- 创作者ID/关键词等
    target_value TEXT,                            -- 具体的值（JSON格式）
    
    -- 创作者模式专用字段
    last_note_id VARCHAR(255),                    -- 该创作者的最新笔记ID
    last_note_time BIGINT,                        -- 该创作者的最新笔记时间
    last_note_title TEXT,                         -- 该创作者的最新笔记标题
    
    -- 搜索模式专用字段
    last_search_time BIGINT,                      -- 上次搜索获取的最新内容时间
    processed_note_ids TEXT,                      -- 已处理的笔记ID列表(JSON)
    
    -- 通用字段
    last_crawl_time BIGINT,                       -- 上次爬取时间戳
    total_crawled INTEGER DEFAULT 0,              -- 累计爬取数量
    incremental_enabled INTEGER DEFAULT 1,        -- 是否启用增量(1启用/0禁用)
    
    created_at BIGINT,
    updated_at BIGINT
);

-- 创建联合唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_type_target 
ON incremental_metadata(platform, crawler_type, target_key);

-- 创建普通索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_platform ON incremental_metadata(platform);
CREATE INDEX IF NOT EXISTS idx_crawler_type ON incremental_metadata(crawler_type);
CREATE INDEX IF NOT EXISTS idx_last_crawl_time ON incremental_metadata(last_crawl_time);

-- 插入说明注释（仅用于文档目的）
-- 
-- 使用说明:
-- 1. 如果使用SQLite，直接执行本脚本即可
-- 2. 如果使用MySQL/PostgreSQL，需要根据对应语法修改:
--    - 将 AUTOINCREMENT 改为 AUTO_INCREMENT (MySQL) 或 SERIAL (PostgreSQL)
--    - 调整数据类型映射
-- 3. 迁移后建议备份原数据库
-- 
-- 验证迁移:
-- SELECT * FROM incremental_metadata LIMIT 1;

