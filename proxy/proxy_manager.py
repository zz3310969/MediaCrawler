# -*- coding: utf-8 -*-
# @Desc    : 代理核心管理器 - 统一管理所有代理相关功能

import asyncio
from typing import Dict, List, Optional, TYPE_CHECKING

from tools.utils import utils

from config.proxy_config_loader import (
    ProxyConfig,
    load_proxy_config,
    SourceConfig,
)

from .binding import AccountProxyBindingManager
from .failover.manager import ProxyFailoverManager
from .failover.strategy import (
    CircuitBreakerStrategy,
    StickyFailoverStrategy,
    SimpleFailoverStrategy,
    WeightedFailoverStrategy,
)
from .persistence.proxy_store import ProxyStore
from .persistence.binding_store import BindingStore
from .persistence.backends.sqlite_backend import SqliteProxyStore, SqliteBindingStore
from .persistence.backends.json_backend import JsonProxyStore, JsonBindingStore
from .providers.custom_api_proxy import CustomApiProxy, CustomApiConfig
from .providers.local_file_proxy import LocalFileProxy
from .quality.evaluator import ProxyQualityEvaluator
from .quality.auto_retirer import AutoProxyRetirer
from .statistics.collector import ProxyStatisticsCollector
from .statistics.store import SQLiteStatisticsStore
from .types import IpInfoModel, PersistedProxy, ProxySource

if TYPE_CHECKING:
    from .base_proxy import ProxyProvider


class ProxyManager:
    """
    代理核心管理器
    
    功能:
    - 统一管理所有代理来源
    - 整合绑定、质量、故障转移、统计模块
    - 提供统一的代理获取接口
    - 支持配置文件驱动
    
    使用方式:
    ```python
    # 使用配置文件初始化
    manager = ProxyManager.from_config("config/proxy_config.yaml")
    await manager.start()
    
    # 获取代理
    proxy = await manager.get_proxy()
    
    # 为账号获取代理
    proxy = await manager.get_proxy_for_account("account_id", "platform")
    
    # 停止
    await manager.stop()
    ```
    """
    
    def __init__(
        self,
        config: Optional[ProxyConfig] = None,
    ):
        """
        初始化代理管理器
        
        Args:
            config: 代理配置，为空则使用默认配置
        """
        self._config = config or ProxyConfig()
        
        # 存储
        self._proxy_store: Optional[ProxyStore] = None
        self._binding_store: Optional[BindingStore] = None
        self._stats_store: Optional[SQLiteStatisticsStore] = None
        
        # 模块
        self._binding_manager: Optional[AccountProxyBindingManager] = None
        self._quality_evaluator: Optional[ProxyQualityEvaluator] = None
        self._failover_manager: Optional[ProxyFailoverManager] = None
        self._auto_retirer: Optional[AutoProxyRetirer] = None
        self._stats_collector: Optional[ProxyStatisticsCollector] = None
        
        # 代理来源
        self._providers: Dict[str, "ProxyProvider"] = {}
        
        # 状态
        self._running = False
        self._initialized = False
    
    @classmethod
    def from_config(cls, config_path: str = "config/proxy_config.yaml") -> "ProxyManager":
        """
        从配置文件创建管理器
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            ProxyManager实例
        """
        config = load_proxy_config(config_path)
        return cls(config=config)
    
    async def start(self) -> None:
        """启动代理管理器"""
        if self._running:
            return
        
        utils.logger.info("[ProxyManager] Starting...")
        
        # 初始化存储
        await self._init_storage()
        
        # 初始化模块
        await self._init_modules()
        
        # 初始化代理来源
        await self._init_providers()
        
        # 启动后台任务
        await self._start_background_tasks()
        
        self._running = True
        self._initialized = True
        utils.logger.info("[ProxyManager] Started successfully")
    
    async def stop(self) -> None:
        """停止代理管理器"""
        if not self._running:
            return
        
        utils.logger.info("[ProxyManager] Stopping...")
        
        # 停止后台任务
        if self._auto_retirer:
            await self._auto_retirer.stop()
        if self._stats_collector:
            await self._stats_collector.stop()
        
        # 关闭存储
        if self._proxy_store:
            await self._proxy_store.close()
        if self._binding_store:
            await self._binding_store.close()
        if self._stats_store:
            await self._stats_store.close()
        
        self._running = False
        utils.logger.info("[ProxyManager] Stopped")
    
    async def _init_storage(self) -> None:
        """初始化存储层"""
        persistence = self._config.persistence
        
        if persistence.backend == "sqlite":
            self._proxy_store = SqliteProxyStore(db_path=persistence.database_path)
            self._binding_store = SqliteBindingStore(db_path=persistence.database_path)
        else:
            self._proxy_store = JsonProxyStore(file_path=f"{persistence.json_data_dir}/proxies.json")
            self._binding_store = JsonBindingStore(file_path=f"{persistence.json_data_dir}/bindings.json")
        
        await self._proxy_store.init()
        await self._binding_store.init()
        
        # 统计存储（始终使用SQLite）
        if self._config.statistics.enabled:
            self._stats_store = SQLiteStatisticsStore(db_path="data/proxy_stats.db")
            await self._stats_store.init()
    
    async def _init_modules(self) -> None:
        """初始化功能模块"""
        global_settings = self._config.global_settings
        
        # 质量评估器
        if self._config.quality.enabled:
            self._quality_evaluator = ProxyQualityEvaluator(
                proxy_store=self._proxy_store,
                sample_window=self._config.quality.sample_window,
                time_window_hours=self._config.quality.time_window_hours,
            )
        
        # 故障转移管理器
        if self._config.failover.enabled:
            strategy = self._create_failover_strategy()
            self._failover_manager = ProxyFailoverManager(
                proxy_store=self._proxy_store,
                strategy=strategy,
                quality_evaluator=self._quality_evaluator,
                max_retries=self._config.failover.max_retries,
                retry_delay_seconds=self._config.failover.retry_delay_seconds,
            )
        
        # 绑定管理器
        if global_settings.enable_binding:
            self._binding_manager = AccountProxyBindingManager(
                proxy_store=self._proxy_store,
                binding_store=self._binding_store,
                max_bindings_per_proxy=global_settings.max_bindings_per_proxy,
                prefer_similar_region=global_settings.prefer_similar_region,
            )
        
        # 自动淘汰器
        if self._config.quality.auto_retire_enabled and self._quality_evaluator:
            self._auto_retirer = AutoProxyRetirer(
                proxy_store=self._proxy_store,
                binding_store=self._binding_store,
                evaluator=self._quality_evaluator,
                min_quality_score=self._config.quality.min_quality_score,
                min_requests_for_retire=self._config.quality.min_requests_for_retire,
                max_consecutive_failures=self._config.quality.max_consecutive_failures,
                check_interval_seconds=self._config.quality.check_interval_seconds,
            )
        
        # 统计收集器
        if self._config.statistics.enabled and self._stats_store:
            self._stats_collector = ProxyStatisticsCollector(
                store=self._stats_store,
                flush_interval_seconds=self._config.statistics.collection_interval_seconds,
            )
    
    def _create_failover_strategy(self):
        """创建故障转移策略"""
        failover = self._config.failover
        
        if failover.strategy == "simple":
            return SimpleFailoverStrategy(max_retries=failover.max_retries)
        elif failover.strategy == "sticky":
            return StickyFailoverStrategy(
                failure_threshold=failover.sticky_failure_threshold,
                recovery_time_seconds=failover.sticky_recovery_time,
            )
        elif failover.strategy == "weighted":
            return WeightedFailoverStrategy()
        else:  # circuit_breaker
            return CircuitBreakerStrategy(
                failure_threshold=failover.cb_failure_threshold,
                recovery_timeout_seconds=failover.cb_recovery_timeout,
                half_open_max_calls=failover.cb_half_open_max_calls,
            )
    
    async def _init_providers(self) -> None:
        """初始化代理来源"""
        for source in self._config.sources:
            if not source.enabled:
                continue
            
            try:
                provider = self._create_provider(source)
                if provider:
                    self._providers[source.name] = provider
                    utils.logger.info(f"[ProxyManager] Initialized provider: {source.name}")
            except Exception as e:
                utils.logger.error(f"[ProxyManager] Failed to init provider {source.name}: {e}")
    
    def _create_provider(self, source: SourceConfig) -> Optional["ProxyProvider"]:
        """创建代理Provider"""
        if source.name == "local_file":
            return LocalFileProxy(
                file_path=source.file_path,
                auto_reload=source.auto_reload,
                default_protocol=source.default_protocol,
                default_expired_seconds=source.default_expired_seconds,
            )
        elif source.name in ("kuaidaili", "wandou"):
            # 商业代理Provider在其他地方初始化
            return None
        elif source.name.startswith("custom") or source.api_url:
            return CustomApiProxy(CustomApiConfig(
                name=source.name,
                url=source.api_url,
                method=source.method,
                headers=source.headers,
                params=source.params,
                body=source.body,
                response_type=source.response_type,
                data_path=source.data_path,
                field_mapping=source.field_mapping,
                rate_limit_per_minute=source.rate_limit_per_minute,
                min_interval_seconds=source.min_interval_seconds,
            ))
        
        return None
    
    async def _start_background_tasks(self) -> None:
        """启动后台任务"""
        if self._auto_retirer:
            await self._auto_retirer.start()
        if self._stats_collector:
            await self._stats_collector.start()
    
    # ==================== 代理获取接口 ====================
    
    async def get_proxy(
        self,
        protocol: Optional[str] = None,
        source: Optional[str] = None,
        failed_proxy_id: Optional[str] = None,
    ) -> Optional[IpInfoModel]:
        """
        获取代理
        
        Args:
            protocol: 协议筛选 (http/https/socks5)
            source: 指定来源
            failed_proxy_id: 上次失败的代理ID
            
        Returns:
            代理信息
        """
        if not self._running:
            await self.start()
        
        # 使用故障转移管理器
        if self._failover_manager:
            return await self._failover_manager.get_proxy(
                failed_proxy_id=failed_proxy_id,
                protocol=protocol,
            )
        
        # 直接从存储获取
        proxies = await self._proxy_store.get_available_proxies(
            protocol=protocol,
            limit=1,
        )
        
        if proxies:
            return proxies[0].to_ip_info_model()
        
        # 从Provider获取
        return await self._get_from_providers(protocol, source)
    
    async def get_proxy_for_account(
        self,
        account_id: str,
        platform: str,
        auto_bind: bool = True,
        auto_rebind: bool = True,
    ) -> Optional[IpInfoModel]:
        """
        为账号获取代理
        
        Args:
            account_id: 账号ID
            platform: 平台
            auto_bind: 无绑定时自动绑定
            auto_rebind: 代理过期时自动重绑
            
        Returns:
            代理信息
        """
        if not self._running:
            await self.start()
        
        if not self._binding_manager:
            return await self.get_proxy()
        
        return await self._binding_manager.get_proxy_for_account(
            account_id=account_id,
            platform=platform,
            auto_bind=auto_bind,
            auto_rebind=auto_rebind,
        )
    
    async def _get_from_providers(
        self,
        protocol: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Optional[IpInfoModel]:
        """从Provider获取代理"""
        providers = list(self._providers.values())
        if source and source in self._providers:
            providers = [self._providers[source]]
        
        for provider in providers:
            try:
                proxies = await provider.get_proxy(1)
                if proxies:
                    proxy = proxies[0]
                    if protocol and proxy.protocol != protocol:
                        continue
                    
                    # 保存到存储
                    persisted = PersistedProxy.from_ip_info_model(proxy, source=provider.__class__.__name__)
                    await self._proxy_store.save_proxy(persisted)
                    
                    return proxy
            except Exception as e:
                utils.logger.error(f"[ProxyManager] Failed to get proxy from {provider}: {e}")
        
        return None
    
    # ==================== 代理管理接口 ====================
    
    async def import_proxies(
        self,
        proxies: List[IpInfoModel],
        source: str = ProxySource.MANUAL.value,
    ) -> int:
        """
        导入代理
        
        Args:
            proxies: 代理列表
            source: 来源标识
            
        Returns:
            成功导入数量
        """
        persisted = [
            PersistedProxy.from_ip_info_model(p, source=source)
            for p in proxies
        ]
        return await self._proxy_store.save_proxies(persisted)
    
    async def get_all_proxies(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersistedProxy]:
        """获取所有代理"""
        return await self._proxy_store.get_all_proxies(
            source=source,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
    
    async def delete_proxy(self, proxy_id: str) -> bool:
        """删除代理"""
        return await self._proxy_store.delete_proxy(proxy_id)
    
    async def update_proxy_status(self, proxy_id: str, is_active: bool) -> bool:
        """更新代理状态"""
        return await self._proxy_store.update_proxy_status(proxy_id, is_active)
    
    # ==================== 绑定管理接口 ====================
    
    async def bind_proxy(
        self,
        account_id: str,
        platform: str,
        proxy_id: str,
        is_sticky: bool = True,
    ) -> bool:
        """绑定代理到账号"""
        if not self._binding_manager:
            return False
        
        try:
            await self._binding_manager.bind(
                account_id=account_id,
                platform=platform,
                proxy_id=proxy_id,
                is_sticky=is_sticky,
            )
            return True
        except Exception as e:
            utils.logger.error(f"[ProxyManager] Failed to bind proxy: {e}")
            return False
    
    async def unbind_proxy(self, account_id: str, platform: str) -> bool:
        """解绑代理"""
        if not self._binding_manager:
            return False
        
        return await self._binding_manager.unbind(account_id, platform)
    
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """获取所有绑定"""
        if not self._binding_manager:
            return []
        
        return await self._binding_manager.get_all_bindings(
            platform=platform,
            limit=limit,
            offset=offset,
        )
    
    # ==================== 质量与统计接口 ====================
    
    async def record_request_result(
        self,
        proxy_id: str,
        platform: str,
        success: bool,
        response_time_ms: float = 0,
        account_id: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        记录请求结果
        
        Args:
            proxy_id: 代理ID
            platform: 平台
            success: 是否成功
            response_time_ms: 响应时间
            account_id: 账号ID
            error_type: 错误类型
        """
        # 记录质量指标
        if self._quality_evaluator:
            if success:
                await self._quality_evaluator.record_success(proxy_id, response_time_ms)
            else:
                await self._quality_evaluator.record_failure(
                    proxy_id,
                    is_timeout="timeout" in (error_type or "").lower(),
                    error_type=error_type,
                )
        
        # 记录统计
        if self._stats_collector:
            await self._stats_collector.record(
                proxy_id=proxy_id,
                platform=platform,
                success=success,
                response_time_ms=response_time_ms,
                account_id=account_id,
                error_type=error_type,
            )
    
    async def get_proxy_quality(self, proxy_id: str) -> Dict:
        """获取代理质量信息"""
        if not self._quality_evaluator:
            return {}
        
        metrics = await self._quality_evaluator.get_metrics(proxy_id)
        return {
            "proxy_id": proxy_id,
            "total_requests": metrics.total_requests,
            "success_rate": metrics.success_rate,
            "avg_response_time": metrics.avg_response_time,
            "quality_score": metrics.quality_score,
            "consecutive_failures": metrics.consecutive_failures,
        }
    
    async def get_statistics(
        self,
        proxy_id: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> Dict:
        """获取统计信息"""
        if not self._stats_collector:
            return {}
        
        if proxy_id:
            return self._stats_collector.get_realtime_stats(proxy_id)
        
        return {
            "all_proxies": self._stats_collector.get_all_realtime_stats(),
        }
    
    # ==================== 属性访问 ====================
    
    @property
    def binding_manager(self) -> Optional[AccountProxyBindingManager]:
        """获取绑定管理器"""
        return self._binding_manager
    
    @property
    def quality_evaluator(self) -> Optional[ProxyQualityEvaluator]:
        """获取质量评估器"""
        return self._quality_evaluator
    
    @property
    def failover_manager(self) -> Optional[ProxyFailoverManager]:
        """获取故障转移管理器"""
        return self._failover_manager
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    @property
    def config(self) -> ProxyConfig:
        """获取配置"""
        return self._config


# 便捷函数
async def create_proxy_manager(
    config_path: str = "config/proxy_config.yaml",
) -> ProxyManager:
    """
    创建并启动代理管理器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        已启动的ProxyManager实例
    """
    manager = ProxyManager.from_config(config_path)
    await manager.start()
    return manager


# 全局单例
_global_manager: Optional[ProxyManager] = None


async def get_proxy_manager() -> ProxyManager:
    """
    获取全局代理管理器单例
    
    Returns:
        ProxyManager实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = await create_proxy_manager()
    return _global_manager


async def shutdown_proxy_manager() -> None:
    """关闭全局代理管理器"""
    global _global_manager
    if _global_manager:
        await _global_manager.stop()
        _global_manager = None

