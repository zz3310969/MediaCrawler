# 反爬增强配置示例

# 功能开关
ENABLE_ANTI_DETECT = True  # 启用反爬增强
ENABLE_FINGERPRINT = True  # 启用浏览器指纹
ENABLE_RATE_LIMIT = True  # 启用智能限速
ENABLE_HUMAN_BEHAVIOR = True  # 启用人类行为模拟
ENABLE_ACCOUNT_HEALTH = True  # 启用账号健康管理
ENABLE_BINDING = True  # 启用账号-代理-指纹绑定

# 指纹配置
FINGERPRINT_PLATFORM_HINT = "mac"  # 平台提示: "mac", "windows", "linux", None
FINGERPRINT_STORAGE_PATH = "data/fingerprints.json"

# 限速配置
RATE_LIMIT_MIN_INTERVAL = 3.0  # 最小请求间隔（秒）
RATE_LIMIT_MAX_INTERVAL = 10.0  # 最大请求间隔（秒）
RATE_LIMIT_HOURLY_LIMIT = 150  # 每小时最大请求数
RATE_LIMIT_DAILY_LIMIT = 1500  # 每天最大请求数
RATE_LIMIT_BURST_PROBABILITY = 0.1  # 快速连续请求概率
RATE_LIMIT_PAUSE_PROBABILITY = 0.05  # 长时间停顿概率
RATE_LIMIT_PAUSE_DURATION = (30, 120)  # 停顿时长范围（秒）

# 人类行为配置
HUMAN_SCROLL_ENABLED = True  # 启用人类滚动
HUMAN_CLICK_ENABLED = True  # 启用人类点击
HUMAN_TYPE_ENABLED = True  # 启用人类打字
HUMAN_BROWSE_DURATION = 5.0  # 随机浏览时长（秒）

# 账号健康配置
ACCOUNT_HEALTH_STORAGE_PATH = "data/account_health.json"
ACCOUNT_COOLING_THRESHOLD = 70.0  # 冷却阈值（风险评分）
ACCOUNT_WARNING_THRESHOLD = 50.0  # 警告阈值（风险评分）
ACCOUNT_COOLING_DURATION = 3600  # 冷却时长（秒）

# 绑定配置
BINDING_STORAGE_PATH = "data/anti_detect_bindings.json"
BINDING_AUTO_CREATE_FINGERPRINT = True  # 自动创建指纹
BINDING_STICKY_PROXY = True  # 粘性代理（保持绑定）

# 平台特定配置
PLATFORM_CONFIGS = {
    "xhs": {
        "rate_limit_min_interval": 3.0,
        "rate_limit_max_interval": 10.0,
        "rate_limit_hourly_limit": 150,
        "rate_limit_daily_limit": 1500,
    },
    "dy": {
        "rate_limit_min_interval": 2.5,
        "rate_limit_max_interval": 8.0,
        "rate_limit_hourly_limit": 180,
        "rate_limit_daily_limit": 1800,
    },
    "wb": {
        "rate_limit_min_interval": 2.0,
        "rate_limit_max_interval": 7.0,
        "rate_limit_hourly_limit": 200,
        "rate_limit_daily_limit": 2000,
    },
    "bili": {
        "rate_limit_min_interval": 2.0,
        "rate_limit_max_interval": 6.0,
        "rate_limit_hourly_limit": 250,
        "rate_limit_daily_limit": 2500,
    },
    "ks": {
        "rate_limit_min_interval": 2.5,
        "rate_limit_max_interval": 8.0,
        "rate_limit_hourly_limit": 180,
        "rate_limit_daily_limit": 1800,
    },
}
