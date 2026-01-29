# -*- coding: utf-8 -*-
# @Desc    : 代理存储抽象接口

from abc import ABC, abstractmethod
from typing import List, Optional

from proxy.types import PersistedProxy, AccountProxyBinding, ProxyQualityMetrics


class ProxyStore(ABC):
    """代理存储抽象接口"""
    
    @abstractmethod
    async def init(self) -> None:
        """初始化存储"""
        raise NotImplementedError
    
    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        raise NotImplementedError
    
    # ==================== 代理CRUD ====================
    
    @abstractmethod
    async def save_proxy(self, proxy: PersistedProxy) -> None:
        """保存代理"""
        raise NotImplementedError
    
    @abstractmethod
    async def save_proxies(self, proxies: List[PersistedProxy]) -> int:
        """批量保存代理，返回保存数量"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_proxy(self, proxy_id: str) -> Optional[PersistedProxy]:
        """获取代理"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_proxy_by_address(self, ip: str, port: int) -> Optional[PersistedProxy]:
        """通过地址获取代理"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_all_proxies(
        self,
        source: Optional[str] = None,
        protocol: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersistedProxy]:
        """获取代理列表"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_available_proxies(
        self,
        protocol: Optional[str] = None,
        min_quality_score: float = 0.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """获取可用代理列表"""
        raise NotImplementedError
    
    @abstractmethod
    async def update_proxy(self, proxy: PersistedProxy) -> bool:
        """更新代理"""
        raise NotImplementedError
    
    @abstractmethod
    async def update_proxy_status(self, proxy_id: str, is_active: bool) -> bool:
        """更新代理状态"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_proxy(self, proxy_id: str) -> bool:
        """删除代理"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_expired_proxies(self) -> int:
        """删除过期代理，返回删除数量"""
        raise NotImplementedError
    
    @abstractmethod
    async def count_proxies(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """统计代理数量"""
        raise NotImplementedError
    
    # ==================== 质量指标 ====================
    
    @abstractmethod
    async def save_quality_metrics(self, metrics: ProxyQualityMetrics) -> None:
        """保存质量指标"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_quality_metrics(self, proxy_id: str) -> Optional[ProxyQualityMetrics]:
        """获取质量指标"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_proxies_by_quality(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """按质量分获取代理"""
        raise NotImplementedError


class BindingStore(ABC):
    """账号-代理绑定存储抽象接口"""
    
    @abstractmethod
    async def init(self) -> None:
        """初始化存储"""
        raise NotImplementedError
    
    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        raise NotImplementedError
    
    # ==================== 绑定CRUD ====================
    
    @abstractmethod
    async def save_binding(self, binding: AccountProxyBinding) -> None:
        """保存绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_binding(
        self,
        account_id: str,
        platform: str,
    ) -> Optional[AccountProxyBinding]:
        """获取绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_binding_by_id(self, binding_id: str) -> Optional[AccountProxyBinding]:
        """通过ID获取绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_bindings_by_proxy(self, proxy_id: str) -> List[AccountProxyBinding]:
        """获取使用指定代理的所有绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccountProxyBinding]:
        """获取绑定列表"""
        raise NotImplementedError
    
    @abstractmethod
    async def update_binding(self, binding: AccountProxyBinding) -> bool:
        """更新绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_binding(self, account_id: str, platform: str) -> bool:
        """删除绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_binding_by_id(self, binding_id: str) -> bool:
        """通过ID删除绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def count_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计绑定数量"""
        raise NotImplementedError
    
    @abstractmethod
    async def count_bindings_by_proxy(self, proxy_id: str) -> int:
        """统计代理的绑定数量"""
        raise NotImplementedError
