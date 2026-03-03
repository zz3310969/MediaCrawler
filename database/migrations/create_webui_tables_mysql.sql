-- WebUI 相关表结构 (MySQL版本)
-- 包含用户管理、任务管理、账号管理、代理管理等
-- 
-- 使用方法:
--   mysql -u root -p media_crawler < create_webui_tables_mysql.sql

-- ============================================
-- 1. 用户表 (User)
-- ============================================
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` VARCHAR(64) NOT NULL UNIQUE,
    `username` VARCHAR(128) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) DEFAULT '',
    `nickname` VARCHAR(128) DEFAULT '',
    `avatar` TEXT,
    `role` VARCHAR(32) DEFAULT 'user',
    `status` VARCHAR(32) DEFAULT 'active',
    `last_login_at` BIGINT DEFAULT 0,
    `last_login_ip` VARCHAR(64) DEFAULT '',
    `created_at` BIGINT NOT NULL,
    `updated_at` BIGINT NOT NULL,
    INDEX `idx_user_status` (`status`),
    INDEX `idx_user_user_id` (`user_id`),
    INDEX `idx_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. 爬虫任务表 (CrawlerTask)
-- ============================================
CREATE TABLE IF NOT EXISTS `crawler_task` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL UNIQUE,
    `user_id` VARCHAR(64) DEFAULT '',
    `session_id` VARCHAR(64) DEFAULT '',
    `task_name` VARCHAR(255) DEFAULT '',
    `platform` VARCHAR(32) NOT NULL,
    `crawler_type` VARCHAR(32) DEFAULT 'search',
    `status` VARCHAR(32) DEFAULT 'pending',
    `priority` INT DEFAULT 5,
    `config` TEXT,
    `progress` TEXT,
    `result` TEXT,
    `task_metadata` TEXT,
    `retry_count` INT DEFAULT 0,
    `max_retries` INT DEFAULT 3,
    `error_message` TEXT,
    `created_at` BIGINT NOT NULL,
    `scheduled_at` BIGINT DEFAULT 0,
    `started_at` BIGINT DEFAULT 0,
    `finished_at` BIGINT DEFAULT 0,
    `last_heartbeat_at` BIGINT DEFAULT 0,
    INDEX `idx_task_user_id` (`user_id`),
    INDEX `idx_task_session_id` (`session_id`),
    INDEX `idx_task_platform` (`platform`),
    INDEX `idx_task_status` (`status`),
    INDEX `idx_task_status_platform` (`status`, `platform`),
    INDEX `idx_task_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. 任务日志表 (TaskLog)
-- ============================================
CREATE TABLE IF NOT EXISTS `task_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `log_id` VARCHAR(64) NOT NULL UNIQUE,
    `task_id` VARCHAR(64) NOT NULL,
    `level` VARCHAR(16) DEFAULT 'info',
    `message` TEXT,
    `extra` TEXT,
    `created_at` BIGINT NOT NULL,
    INDEX `idx_log_task_id` (`task_id`),
    INDEX `idx_log_level` (`level`),
    INDEX `idx_log_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. 爬虫账号表 (CrawlerAccount)
-- ============================================
CREATE TABLE IF NOT EXISTS `crawler_account` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `account_id` VARCHAR(64) NOT NULL UNIQUE,
    `platform` VARCHAR(32) NOT NULL,
    `username` VARCHAR(255) DEFAULT '',
    `nickname` VARCHAR(255) DEFAULT '',
    `avatar` TEXT,
    `status` VARCHAR(32) DEFAULT 'pending',
    `login_method` VARCHAR(32) DEFAULT 'cookie',
    `cookies` TEXT,
    `cookie_valid` TINYINT DEFAULT 0,
    `last_used_at` BIGINT DEFAULT 0,
    `last_validated_at` BIGINT DEFAULT 0,
    `expires_at` BIGINT DEFAULT 0,
    `created_at` BIGINT NOT NULL,
    `updated_at` BIGINT NOT NULL,
    `remark` TEXT,
    INDEX `idx_account_platform` (`platform`),
    INDEX `idx_account_status` (`status`),
    INDEX `idx_account_platform_status` (`platform`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. 代理池表 (ProxyPool)
-- ============================================
CREATE TABLE IF NOT EXISTS `proxy_pool` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `proxy_id` VARCHAR(64) NOT NULL UNIQUE,
    `ip` VARCHAR(64) NOT NULL,
    `port` INT NOT NULL,
    `protocol` VARCHAR(16) DEFAULT 'http',
    `username` VARCHAR(255) DEFAULT '',
    `password` VARCHAR(255) DEFAULT '',
    `source` VARCHAR(64) DEFAULT 'manual',
    `country` VARCHAR(32) DEFAULT 'CN',
    `province` VARCHAR(64) DEFAULT '',
    `city` VARCHAR(64) DEFAULT '',
    `isp` VARCHAR(64) DEFAULT '',
    `status` VARCHAR(32) DEFAULT 'testing',
    `is_active` TINYINT DEFAULT 1,
    `quality_score` FLOAT DEFAULT 50.0,
    `response_time` INT DEFAULT 0,
    `total_requests` INT DEFAULT 0,
    `success_requests` INT DEFAULT 0,
    `failed_requests` INT DEFAULT 0,
    `consecutive_failures` INT DEFAULT 0,
    `last_success_at` BIGINT DEFAULT 0,
    `last_failure_at` BIGINT DEFAULT 0,
    `last_checked_at` BIGINT DEFAULT 0,
    `expired_at` BIGINT DEFAULT 0,
    `created_at` BIGINT NOT NULL,
    `updated_at` BIGINT NOT NULL,
    UNIQUE KEY `uk_proxy_ip_port` (`ip`, `port`),
    INDEX `idx_proxy_status` (`status`),
    INDEX `idx_proxy_is_active` (`is_active`),
    INDEX `idx_proxy_quality` (`quality_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. 代理绑定表 (ProxyBinding)
-- ============================================
CREATE TABLE IF NOT EXISTS `proxy_binding` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `binding_id` VARCHAR(64) NOT NULL UNIQUE,
    `account_id` VARCHAR(64) NOT NULL,
    `platform` VARCHAR(32) NOT NULL,
    `proxy_id` VARCHAR(64) NOT NULL,
    `is_sticky` TINYINT DEFAULT 1,
    `status` VARCHAR(32) DEFAULT 'active',
    `rebind_count` INT DEFAULT 0,
    `bound_at` BIGINT NOT NULL,
    `last_used_at` BIGINT DEFAULT 0,
    UNIQUE KEY `uk_binding_account_platform` (`account_id`, `platform`),
    INDEX `idx_binding_account_id` (`account_id`),
    INDEX `idx_binding_proxy_id` (`proxy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 7. 系统配置表 (SystemConfig)
-- ============================================
CREATE TABLE IF NOT EXISTS `system_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_key` VARCHAR(128) NOT NULL UNIQUE,
    `config_value` TEXT,
    `config_type` VARCHAR(32) DEFAULT 'system',
    `description` TEXT,
    `created_at` BIGINT NOT NULL,
    `updated_at` BIGINT NOT NULL,
    INDEX `idx_config_type` (`config_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 初始化默认数据
-- ============================================

-- 创建默认管理员用户 (密码: admin123)
-- 注意: 实际部署时应修改默认密码
INSERT IGNORE INTO `user` (`user_id`, `username`, `password_hash`, `nickname`, `role`, `status`, `created_at`, `updated_at`)
VALUES (
    'admin-001',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.2QqQqQqQqQqQqK',
    '管理员',
    'admin',
    'active',
    UNIX_TIMESTAMP(),
    UNIX_TIMESTAMP()
);

-- 插入默认系统配置
INSERT IGNORE INTO `system_config` (`config_key`, `config_value`, `config_type`, `description`, `created_at`, `updated_at`)
VALUES 
    ('proxy.enabled', 'true', 'proxy', '是否启用代理', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('proxy.pool_size', '5', 'proxy', '代理池大小', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('proxy.validate_on_get', 'true', 'proxy', '获取时验证代理', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('proxy.validate_timeout', '10', 'proxy', '验证超时时间(秒)', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('crawler.default_concurrency', '3', 'crawler', '默认并发数', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('crawler.default_interval', '1.0', 'crawler', '默认请求间隔(秒)', UNIX_TIMESTAMP(), UNIX_TIMESTAMP()),
    ('system.max_tasks_per_user', '10', 'system', '每用户最大任务数', UNIX_TIMESTAMP(), UNIX_TIMESTAMP());
