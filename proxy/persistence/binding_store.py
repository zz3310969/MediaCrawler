# -*- coding: utf-8 -*-
# @Desc    : 账号-代理绑定存储抽象接口

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from proxy.types import AccountProxyBinding


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
        """保存绑定关系"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_binding(self, account_id: str, platform: str) -> Optional[AccountProxyBinding]:
        """获取账号的绑定关系"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_binding_by_id(self, binding_id: str) -> Optional[AccountProxyBinding]:
        """通过绑定ID获取"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_bindings_by_proxy(self, proxy_id: str) -> List[AccountProxyBinding]:
        """获取使用某代理的所有绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccountProxyBinding]:
        """获取所有绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def update_binding(self, binding: AccountProxyBinding) -> bool:
        """更新绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def update_binding_status(self, account_id: str, platform: str, status: str) -> bool:
        """更新绑定状态"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_binding(self, account_id: str, platform: str) -> bool:
        """删除绑定"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete_bindings_by_proxy(self, proxy_id: str) -> int:
        """删除某代理的所有绑定，返回删除数量"""
        raise NotImplementedError
    
    # ==================== 统计 ====================
    
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
        """统计某代理的绑定数量"""
        raise NotImplementedError
    
    @abstractmethod
    async def binding_exists(self, account_id: str, platform: str) -> bool:
        """检查绑定是否存在"""
        raise NotImplementedError
    
    # ==================== 绑定历史 ====================
    
    @abstractmethod
    async def save_binding_history(
        self,
        binding_id: str,
        account_id: str,
        platform: str,
        action: str,
        old_proxy_id: Optional[str] = None,
        new_proxy_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """保存绑定历史"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_binding_history(
        self,
        account_id: str,
        platform: str,
        limit: int = 50,
    ) -> List[Dict]:
        """获取绑定历史"""
        raise NotImplementedError

