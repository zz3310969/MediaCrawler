-- WebUI 相关表结构
-- 包含用户管理、任务管理、账号管理、代理管理等

-- ============================================
-- 1. 用户表 (User)
-- ============================================
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    username VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) DEFAULT '',
    nickname VARCHAR(128) DEFAULT '',
    avatar TEXT DEFAULT '',
    role VARCHAR(32) DEFAULT 'user',
    status VARCHAR(32) DEFAULT 'active',
    last_login_at BIGINT DEFAULT 0,
    last_login_ip VARCHAR(64) DEFAULT '',
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_status ON user(status);

-- ============================================
-- 2. 爬虫任务表 (CrawlerTask)
-- ============================================
CREATE TABLE IF NOT EXISTS crawler_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(64) DEFAULT '',
    session_id VARCHAR(64) DEFAULT '',
    task_name VARCHAR(255) DEFAULT '',
    platform VARCHAR(32) NOT NULL,
    crawler_type VARCHAR(32) DEFAULT 'search',
    status VARCHAR(32) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    config TEXT DEFAULT '{}',
    progress TEXT DEFAULT '{}',
    result TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT DEFAULT '',
    created_at BIGINT NOT NULL,
    scheduled_at BIGINT DEFAULT 0,
    started_at BIGINT DEFAULT 0,
    finished_at BIGINT DEFAULT 0,
    last_heartbeat_at BIGINT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_task_user ON crawler_task(user_id);
CREATE INDEX IF NOT EXISTS idx_task_session ON crawler_task(session_id);
CREATE INDEX IF NOT EXISTS idx_task_platform ON crawler_task(platform);
CREATE INDEX IF NOT EXISTS idx_task_status ON crawler_task(status);
CREATE INDEX IF NOT EXISTS idx_task_status_platform ON crawler_task(status, platform);
CREATE INDEX IF NOT EXISTS idx_task_created ON crawler_task(created_at);

-- ============================================
-- 3. 任务日志表 (TaskLog)
-- ============================================
CREATE TABLE IF NOT EXISTS task_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id VARCHAR(64) NOT NULL UNIQUE,
    task_id VARCHAR(64) NOT NULL,
    level VARCHAR(16) DEFAULT 'info',
    message TEXT DEFAULT '',
    extra TEXT DEFAULT '{}',
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_log_task ON task_log(task_id);
CREATE INDEX IF NOT EXISTS idx_log_level ON task_log(level);
CREATE INDEX IF NOT EXISTS idx_log_created ON task_log(created_at);

-- ============================================
-- 4. 爬虫账号表 (CrawlerAccount)
-- ============================================
CREATE TABLE IF NOT EXISTS crawler_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id VARCHAR(64) NOT NULL UNIQUE,
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(255) DEFAULT '',
    nickname VARCHAR(255) DEFAULT '',
    avatar TEXT DEFAULT '',
    status VARCHAR(32) DEFAULT 'pending',
    login_method VARCHAR(32) DEFAULT 'cookie',
    cookies TEXT DEFAULT '',
    cookie_valid INTEGER DEFAULT 0,
    last_used_at BIGINT DEFAULT 0,
    last_validated_at BIGINT DEFAULT 0,
    expires_at BIGINT DEFAULT 0,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    remark TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_account_platform ON crawler_account(platform);
CREATE INDEX IF NOT EXISTS idx_account_status ON crawler_account(status);
CREATE INDEX IF NOT EXISTS idx_account_platform_status ON crawler_account(platform, status);

-- ============================================
-- 5. 代理池表 (ProxyPool)
-- ============================================
CREATE TABLE IF NOT EXISTS proxy_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proxy_id VARCHAR(64) NOT NULL UNIQUE,
    ip VARCHAR(64) NOT NULL,
    port INTEGER NOT NULL,
    protocol VARCHAR(16) DEFAULT 'http',
    username VARCHAR(255) DEFAULT '',
    password VARCHAR(255) DEFAULT '',
    source VARCHAR(64) DEFAULT 'manual',
    country VARCHAR(32) DEFAULT 'CN',
    province VARCHAR(64) DEFAULT '',
    city VARCHAR(64) DEFAULT '',
    isp VARCHAR(64) DEFAULT '',
    status VARCHAR(32) DEFAULT 'testing',
    is_active INTEGER DEFAULT 1,
    quality_score REAL DEFAULT 50.0,
    response_time INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    success_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_success_at BIGINT DEFAULT 0,
    last_failure_at BIGINT DEFAULT 0,
    last_checked_at BIGINT DEFAULT 0,
    expired_at BIGINT DEFAULT 0,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    UNIQUE(ip, port)
);

CREATE INDEX IF NOT EXISTS idx_proxy_status ON proxy_pool(status);
CREATE INDEX IF NOT EXISTS idx_proxy_is_active ON proxy_pool(is_active);
CREATE INDEX IF NOT EXISTS idx_proxy_quality ON proxy_pool(quality_score);

-- ============================================
-- 6. 代理绑定表 (ProxyBinding)
-- ============================================
CREATE TABLE IF NOT EXISTS proxy_binding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    binding_id VARCHAR(64) NOT NULL UNIQUE,
    account_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    proxy_id VARCHAR(64) NOT NULL,
    is_sticky INTEGER DEFAULT 1,
    status VARCHAR(32) DEFAULT 'active',
    rebind_count INTEGER DEFAULT 0,
    bound_at BIGINT NOT NULL,
    last_used_at BIGINT DEFAULT 0,
    UNIQUE(account_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_binding_account ON proxy_binding(account_id);
CREATE INDEX IF NOT EXISTS idx_binding_proxy ON proxy_binding(proxy_id);

-- ============================================
-- 7. 系统配置表 (SystemConfig)
-- ============================================
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(128) NOT NULL UNIQUE,
    config_value TEXT DEFAULT '',
    config_type VARCHAR(32) DEFAULT 'system',
    description TEXT DEFAULT '',
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_config_type ON system_config(config_type);

-- ============================================
-- 初始化默认数据
-- ============================================

-- 创建默认管理员用户 (密码: admin123, 使用bcrypt哈希)
-- 注意: 实际部署时应修改默认密码
INSERT OR IGNORE INTO user (user_id, username, password_hash, nickname, role, status, created_at, updated_at)
VALUES (
    'admin-001',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.2QqQqQqQqQqQqK',
    '管理员',
    'admin',
    'active',
    strftime('%s', 'now') * 1000,
    strftime('%s', 'now') * 1000
);

-- 插入默认系统配置
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description, created_at, updated_at)
VALUES 
    ('proxy.enabled', 'true', 'proxy', '是否启用代理', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('proxy.pool_size', '5', 'proxy', '代理池大小', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('proxy.validate_on_get', 'true', 'proxy', '获取时验证代理', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('proxy.validate_timeout', '10', 'proxy', '验证超时时间(秒)', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('crawler.default_concurrency', '3', 'crawler', '默认并发数', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('crawler.default_interval', '1.0', 'crawler', '默认请求间隔(秒)', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000),
    ('system.max_tasks_per_user', '10', 'system', '每用户最大任务数', strftime('%s', 'now') * 1000, strftime('%s', 'now') * 1000);
