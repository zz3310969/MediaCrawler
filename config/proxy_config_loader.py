# -*- coding: utf-8 -*-
# @Desc    : 代理配置加载器

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from tools.utils import utils


# 环境变量模式
ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')


def replace_env_vars(value: Any) -> Any:
    """递归替换环境变量"""
    if isinstance(value, str):
        def replace(match):
            var_name = match.group(1)
            return os.environ.get(var_name, "")
        return ENV_VAR_PATTERN.sub(replace, value)
    elif isinstance(value, dict):
        return {k: replace_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [replace_env_vars(item) for item in value]
    return value


@dataclass
class GlobalConfig:
    """全局设置"""
    enable_proxy: bool = True
    proxy_pool_size: int = 5
    validate_on_get: bool = True
    validate_timeout: int = 10
    enable_binding: bool = True
    binding_sticky: bool = True
    auto_rebind: bool = True
    max_bindings_per_proxy: int = 5
    prefer_similar_region: bool = True


@dataclass
class PersistenceConfig:
    """持久化设置"""
    backend: str = "sqlite"
    database_path: str = "data/proxy.db"
    json_data_dir: str = "data/proxy"


@dataclass
class SourceConfig:
    """代理来源配置"""
    enabled: bool = False
    priority: int = 1
    name: str = ""
    
    # 通用字段
    api_url: str = ""
    api_key: str = ""
    
    # 本地文件
    file_path: str = ""
    auto_reload: bool = True
    default_protocol: str = "http"
    default_expired_seconds: Optional[int] = None
    
    # 自定义API
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    response_type: str = "json"
    data_path: str = ""
    field_mapping: Dict[str, str] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    min_interval_seconds: float = 1.0
    
    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityConfig:
    """质量评估设置"""
    enabled: bool = True
    sample_window: int = 100
    time_window_hours: int = 24
    min_quality_score: float = 30
    min_requests_for_retire: int = 20
    max_consecutive_failures: int = 10
    auto_retire_enabled: bool = True
    check_interval_seconds: int = 300


@dataclass
class FailoverConfig:
    """故障转移设置"""
    enabled: bool = True
    strategy: str = "circuit_breaker"
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # 熔断器
    cb_failure_threshold: int = 5
    cb_recovery_timeout: int = 60
    cb_half_open_max_calls: int = 3
    
    # 粘性
    sticky_failure_threshold: int = 3
    sticky_recovery_time: int = 300


@dataclass
class StatisticsConfig:
    """统计设置"""
    enabled: bool = True
    collection_interval_seconds: int = 60
    retention_days: int = 30
    log_requests: bool = True
    log_response_samples: bool = True
    max_samples_per_proxy: int = 100


@dataclass
class ProxyConfig:
    """完整代理配置"""
    global_settings: GlobalConfig = field(default_factory=GlobalConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    sources: List[SourceConfig] = field(default_factory=list)
    quality: QualityConfig = field(default_factory=QualityConfig)
    failover: FailoverConfig = field(default_factory=FailoverConfig)
    statistics: StatisticsConfig = field(default_factory=StatisticsConfig)


def load_proxy_config(config_path: str = "config/proxy_config.yaml") -> ProxyConfig:
    """
    加载代理配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ProxyConfig实例
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        utils.logger.warning(f"[ProxyConfigLoader] Config file not found: {config_path}, using defaults")
        return ProxyConfig()
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
        
        # 替换环境变量
        config_data = replace_env_vars(raw_config)
        
        return _parse_config(config_data)
        
    except Exception as e:
        utils.logger.error(f"[ProxyConfigLoader] Failed to load config: {e}")
        return ProxyConfig()


def _parse_config(data: Dict[str, Any]) -> ProxyConfig:
    """解析配置数据"""
    config = ProxyConfig()
    
    # 解析全局设置
    if "global" in data:
        g = data["global"]
        config.global_settings = GlobalConfig(
            enable_proxy=g.get("enable_proxy", True),
            proxy_pool_size=g.get("proxy_pool_size", 5),
            validate_on_get=g.get("validate_on_get", True),
            validate_timeout=g.get("validate_timeout", 10),
            enable_binding=g.get("enable_binding", True),
            binding_sticky=g.get("binding_sticky", True),
            auto_rebind=g.get("auto_rebind", True),
            max_bindings_per_proxy=g.get("max_bindings_per_proxy", 5),
            prefer_similar_region=g.get("prefer_similar_region", True),
        )
    
    # 解析持久化设置
    if "persistence" in data:
        p = data["persistence"]
        config.persistence = PersistenceConfig(
            backend=p.get("backend", "sqlite"),
            database_path=p.get("database_path", "data/proxy.db"),
            json_data_dir=p.get("json_data_dir", "data/proxy"),
        )
    
    # 解析代理来源
    if "sources" in data:
        sources = data["sources"]
        
        # 快代理
        if "kuaidaili" in sources:
            s = sources["kuaidaili"]
            if s.get("enabled", False):
                config.sources.append(SourceConfig(
                    enabled=True,
                    priority=s.get("priority", 1),
                    name="kuaidaili",
                    api_url=s.get("api_url", ""),
                    api_key=s.get("api_key", ""),
                    extra={
                        "secret_id": s.get("secret_id", ""),
                        "signature": s.get("signature", ""),
                        "default_num": s.get("default_num", 5),
                    },
                ))
        
        # 万豆代理
        if "wandou" in sources:
            s = sources["wandou"]
            if s.get("enabled", False):
                config.sources.append(SourceConfig(
                    enabled=True,
                    priority=s.get("priority", 2),
                    name="wandou",
                    api_key=s.get("app_key", ""),
                ))
        
        # 本地文件
        if "local_file" in sources:
            s = sources["local_file"]
            if s.get("enabled", False):
                config.sources.append(SourceConfig(
                    enabled=True,
                    priority=s.get("priority", 3),
                    name="local_file",
                    file_path=s.get("file_path", ""),
                    auto_reload=s.get("auto_reload", True),
                    default_protocol=s.get("default_protocol", "http"),
                    default_expired_seconds=s.get("default_expired_seconds"),
                ))
        
        # 自定义API
        if "custom_apis" in sources:
            for api in sources["custom_apis"]:
                if api.get("enabled", False):
                    config.sources.append(SourceConfig(
                        enabled=True,
                        priority=api.get("priority", 10),
                        name=api.get("name", "custom"),
                        api_url=api.get("url", ""),
                        method=api.get("method", "GET"),
                        headers=api.get("headers", {}),
                        params=api.get("params", {}),
                        body=api.get("body"),
                        response_type=api.get("response_type", "json"),
                        data_path=api.get("data_path", ""),
                        field_mapping=api.get("field_mapping", {}),
                        rate_limit_per_minute=api.get("rate_limit_per_minute", 60),
                        min_interval_seconds=api.get("min_interval_seconds", 1.0),
                    ))
        
        # 按优先级排序
        config.sources.sort(key=lambda x: x.priority)
    
    # 解析质量评估设置
    if "quality" in data:
        q = data["quality"]
        auto_retire = q.get("auto_retire", {})
        config.quality = QualityConfig(
            enabled=q.get("enabled", True),
            sample_window=q.get("sample_window", 100),
            time_window_hours=q.get("time_window_hours", 24),
            min_quality_score=q.get("min_quality_score", 30),
            min_requests_for_retire=q.get("min_requests_for_retire", 20),
            max_consecutive_failures=q.get("max_consecutive_failures", 10),
            auto_retire_enabled=auto_retire.get("enabled", True),
            check_interval_seconds=auto_retire.get("check_interval_seconds", 300),
        )
    
    # 解析故障转移设置
    if "failover" in data:
        f = data["failover"]
        cb = f.get("circuit_breaker", {})
        sticky = f.get("sticky", {})
        config.failover = FailoverConfig(
            enabled=f.get("enabled", True),
            strategy=f.get("strategy", "circuit_breaker"),
            max_retries=f.get("max_retries", 3),
            retry_delay_seconds=f.get("retry_delay_seconds", 1.0),
            cb_failure_threshold=cb.get("failure_threshold", 5),
            cb_recovery_timeout=cb.get("recovery_timeout_seconds", 60),
            cb_half_open_max_calls=cb.get("half_open_max_calls", 3),
            sticky_failure_threshold=sticky.get("failure_threshold", 3),
            sticky_recovery_time=sticky.get("recovery_time_seconds", 300),
        )
    
    # 解析统计设置
    if "statistics" in data:
        s = data["statistics"]
        config.statistics = StatisticsConfig(
            enabled=s.get("enabled", True),
            collection_interval_seconds=s.get("collection_interval_seconds", 60),
            retention_days=s.get("retention_days", 30),
            log_requests=s.get("log_requests", True),
            log_response_samples=s.get("log_response_samples", True),
            max_samples_per_proxy=s.get("max_samples_per_proxy", 100),
        )
    
    return config


def save_proxy_config(config: ProxyConfig, config_path: str = "config/proxy_config.yaml") -> bool:
    """
    保存代理配置
    
    Args:
        config: 配置对象
        config_path: 配置文件路径
        
    Returns:
        是否成功
    """
    try:
        # 转换为字典
        data = {
            "global": {
                "enable_proxy": config.global_settings.enable_proxy,
                "proxy_pool_size": config.global_settings.proxy_pool_size,
                "validate_on_get": config.global_settings.validate_on_get,
                "validate_timeout": config.global_settings.validate_timeout,
                "enable_binding": config.global_settings.enable_binding,
                "binding_sticky": config.global_settings.binding_sticky,
                "auto_rebind": config.global_settings.auto_rebind,
                "max_bindings_per_proxy": config.global_settings.max_bindings_per_proxy,
                "prefer_similar_region": config.global_settings.prefer_similar_region,
            },
            "persistence": {
                "backend": config.persistence.backend,
                "database_path": config.persistence.database_path,
                "json_data_dir": config.persistence.json_data_dir,
            },
            "quality": {
                "enabled": config.quality.enabled,
                "sample_window": config.quality.sample_window,
                "time_window_hours": config.quality.time_window_hours,
                "min_quality_score": config.quality.min_quality_score,
                "min_requests_for_retire": config.quality.min_requests_for_retire,
                "max_consecutive_failures": config.quality.max_consecutive_failures,
                "auto_retire": {
                    "enabled": config.quality.auto_retire_enabled,
                    "check_interval_seconds": config.quality.check_interval_seconds,
                },
            },
            "failover": {
                "enabled": config.failover.enabled,
                "strategy": config.failover.strategy,
                "max_retries": config.failover.max_retries,
                "retry_delay_seconds": config.failover.retry_delay_seconds,
                "circuit_breaker": {
                    "failure_threshold": config.failover.cb_failure_threshold,
                    "recovery_timeout_seconds": config.failover.cb_recovery_timeout,
                    "half_open_max_calls": config.failover.cb_half_open_max_calls,
                },
                "sticky": {
                    "failure_threshold": config.failover.sticky_failure_threshold,
                    "recovery_time_seconds": config.failover.sticky_recovery_time,
                },
            },
            "statistics": {
                "enabled": config.statistics.enabled,
                "collection_interval_seconds": config.statistics.collection_interval_seconds,
                "retention_days": config.statistics.retention_days,
                "log_requests": config.statistics.log_requests,
                "log_response_samples": config.statistics.log_response_samples,
                "max_samples_per_proxy": config.statistics.max_samples_per_proxy,
            },
        }
        
        # 保存
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        return True
        
    except Exception as e:
        utils.logger.error(f"[ProxyConfigLoader] Failed to save config: {e}")
        return False

