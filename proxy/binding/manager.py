# -*- coding: utf-8 -*-
# @Desc    : 账号-代理绑定管理器

import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from tools.utils import utils

from ..persistence.proxy_store import ProxyStore
from ..persistence.binding_store import BindingStore
from ..types import (
    AccountProxyBinding,
    BindingStatus,
    IpInfoModel,
    PersistedProxy,
    ProxyRegionInfo,
)

if TYPE_CHECKING:
    from account.account_pool import Account


class AccountProxyBindingManager:
    """
    账号-代理绑定管理器
    
    功能:
    - 为账号绑定代理（支持粘性绑定）
    - 自动重绑定（当代理过期时）
    - 优先选择相似地区的代理
    - 记录绑定历史
    """
    
    def __init__(
        self,
        proxy_store: ProxyStore,
        binding_store: BindingStore,
        max_bindings_per_proxy: int = 5,
        prefer_similar_region: bool = True,
    ):
        """
        初始化绑定管理器
        
        Args:
            proxy_store: 代理存储
            binding_store: 绑定存储
            max_bindings_per_proxy: 每个代理最大绑定数
            prefer_similar_region: 是否优先选择相似地区代理
        """
        self._proxy_store = proxy_store
        self._binding_store = binding_store
        self._max_bindings_per_proxy = max_bindings_per_proxy
        self._prefer_similar_region = prefer_similar_region
        
        # 内存缓存
        self._binding_cache: Dict[str, AccountProxyBinding] = {}
    
    def _get_binding_key(self, account_id: str, platform: str) -> str:
        """生成绑定缓存key"""
        return f"{account_id}:{platform}"
    
    def _generate_binding_id(self, account_id: str, platform: str) -> str:
        """生成绑定ID"""
        key = f"{account_id}:{platform}:{datetime.now().isoformat()}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    async def bind(
        self,
        account_id: str,
        platform: str,
        proxy_id: str,
        is_sticky: bool = True,
        allow_auto_rebind: bool = True,
    ) -> AccountProxyBinding:
        """
        绑定代理到账号
        
        Args:
            account_id: 账号ID
            platform: 平台
            proxy_id: 代理ID
            is_sticky: 是否粘性绑定
            allow_auto_rebind: 是否允许自动重绑
            
        Returns:
            绑定对象
        """
        # 检查代理是否存在
        proxy = await self._proxy_store.get_proxy(proxy_id)
        if not proxy:
            raise ValueError(f"代理不存在: {proxy_id}")
        
        # 检查是否已存在绑定
        existing = await self.get_binding(account_id, platform)
        old_proxy_id = None
        
        if existing:
            old_proxy_id = existing.proxy_id
            # 更新现有绑定
            existing.proxy_id = proxy_id
            existing.is_sticky = is_sticky
            existing.allow_auto_rebind = allow_auto_rebind
            existing.status = BindingStatus.ACTIVE.value
            existing.rebind_count += 1
            await self._binding_store.update_binding(existing)
            binding = existing
            action = "rebind"
        else:
            # 创建新绑定
            binding = AccountProxyBinding(
                binding_id=self._generate_binding_id(account_id, platform),
                account_id=account_id,
                platform=platform,
                proxy_id=proxy_id,
                is_sticky=is_sticky,
                allow_auto_rebind=allow_auto_rebind,
            )
            await self._binding_store.save_binding(binding)
            action = "bind"
        
        # 更新缓存
        cache_key = self._get_binding_key(account_id, platform)
        self._binding_cache[cache_key] = binding
        
        # 记录历史
        await self._binding_store.save_binding_history(
            binding_id=binding.binding_id,
            account_id=account_id,
            platform=platform,
            action=action,
            old_proxy_id=old_proxy_id,
            new_proxy_id=proxy_id,
            reason="手动绑定" if action == "bind" else "重新绑定",
        )
        
        utils.logger.info(f"[BindingManager] 账号 {account_id}@{platform} 绑定代理 {proxy_id}")
        return binding
    
    async def unbind(self, account_id: str, platform: str, reason: str = "手动解绑") -> bool:
        """
        解除绑定
        
        Args:
            account_id: 账号ID
            platform: 平台
            reason: 解绑原因
            
        Returns:
            是否成功解绑
        """
        binding = await self.get_binding(account_id, platform)
        if not binding:
            return False
        
        # 记录历史
        await self._binding_store.save_binding_history(
            binding_id=binding.binding_id,
            account_id=account_id,
            platform=platform,
            action="unbind",
            old_proxy_id=binding.proxy_id,
            reason=reason,
        )
        
        # 删除绑定
        success = await self._binding_store.delete_binding(account_id, platform)
        
        # 清除缓存
        cache_key = self._get_binding_key(account_id, platform)
        self._binding_cache.pop(cache_key, None)
        
        utils.logger.info(f"[BindingManager] 账号 {account_id}@{platform} 解除绑定")
        return success
    
    async def rebind(
        self,
        account_id: str,
        platform: str,
        reason: str = "自动重绑",
        exclude_proxy_ids: Optional[List[str]] = None,
    ) -> Optional[AccountProxyBinding]:
        """
        重新绑定（当代理失效时）
        
        会优先选择与原代理相似地区的代理
        
        Args:
            account_id: 账号ID
            platform: 平台
            reason: 重绑原因
            exclude_proxy_ids: 排除的代理ID列表
            
        Returns:
            新绑定对象，失败返回None
        """
        # 获取原绑定
        binding = await self.get_binding(account_id, platform)
        old_proxy_id = binding.proxy_id if binding else None
        old_proxy = await self._proxy_store.get_proxy(old_proxy_id) if old_proxy_id else None
        
        # 排除列表
        exclude_ids = list(exclude_proxy_ids or [])
        if old_proxy_id:
            exclude_ids.append(old_proxy_id)
        
        # 获取新代理
        new_proxy = await self._find_best_proxy(old_proxy, exclude_ids)
        if not new_proxy:
            utils.logger.warning(f"[BindingManager] 无可用代理进行重绑")
            return None
        
        # 执行绑定
        new_binding = await self.bind(
            account_id=account_id,
            platform=platform,
            proxy_id=new_proxy.proxy_id,
            is_sticky=binding.is_sticky if binding else True,
            allow_auto_rebind=binding.allow_auto_rebind if binding else True,
        )
        
        # 记录历史（覆盖bind方法的记录）
        await self._binding_store.save_binding_history(
            binding_id=new_binding.binding_id,
            account_id=account_id,
            platform=platform,
            action="auto_rebind",
            old_proxy_id=old_proxy_id,
            new_proxy_id=new_proxy.proxy_id,
            reason=reason,
        )
        
        utils.logger.info(
            f"[BindingManager] 账号 {account_id}@{platform} 自动重绑: "
            f"{old_proxy_id} -> {new_proxy.proxy_id}"
        )
        return new_binding
    
    async def get_binding(self, account_id: str, platform: str) -> Optional[AccountProxyBinding]:
        """
        获取账号的绑定关系
        
        Args:
            account_id: 账号ID
            platform: 平台
            
        Returns:
            绑定对象
        """
        # 先查缓存
        cache_key = self._get_binding_key(account_id, platform)
        if cache_key in self._binding_cache:
            return self._binding_cache[cache_key]
        
        # 查数据库
        binding = await self._binding_store.get_binding(account_id, platform)
        if binding:
            self._binding_cache[cache_key] = binding
        return binding
    
    async def get_proxy_for_account(
        self,
        account_id: str,
        platform: str,
        auto_bind: bool = True,
        auto_rebind: bool = True,
    ) -> Optional[IpInfoModel]:
        """
        获取账号绑定的代理
        
        核心方法：自动处理绑定、过期检测、重绑定
        
        Args:
            account_id: 账号ID
            platform: 平台
            auto_bind: 无绑定时是否自动绑定
            auto_rebind: 代理过期时是否自动重绑
            
        Returns:
            代理信息
        """
        # 获取绑定
        binding = await self.get_binding(account_id, platform)
        
        if not binding:
            if not auto_bind:
                return None
            # 自动绑定
            binding = await self._auto_bind(account_id, platform)
            if not binding:
                return None
        
        # 获取代理
        proxy = await self._proxy_store.get_proxy(binding.proxy_id)
        
        if not proxy or not proxy.is_active:
            if not auto_rebind or not binding.allow_auto_rebind:
                # 标记绑定过期
                await self._binding_store.update_binding_status(
                    account_id, platform, BindingStatus.EXPIRED.value
                )
                return None
            # 自动重绑
            binding = await self.rebind(account_id, platform, reason="代理不可用")
            if not binding:
                return None
            proxy = await self._proxy_store.get_proxy(binding.proxy_id)
        
        # 检查代理是否过期
        ip_info = proxy.to_ip_info_model()
        if ip_info.is_expired():
            if not auto_rebind or not binding.allow_auto_rebind:
                await self._binding_store.update_binding_status(
                    account_id, platform, BindingStatus.EXPIRED.value
                )
                return None
            # 自动重绑
            binding = await self.rebind(account_id, platform, reason="代理已过期")
            if not binding:
                return None
            proxy = await self._proxy_store.get_proxy(binding.proxy_id)
            ip_info = proxy.to_ip_info_model()
        
        # 更新使用时间
        binding.mark_used()
        await self._binding_store.update_binding(binding)
        
        return ip_info
    
    async def _auto_bind(self, account_id: str, platform: str) -> Optional[AccountProxyBinding]:
        """自动绑定代理"""
        # 获取可用代理
        proxies = await self._proxy_store.get_available_proxies(limit=10)
        if not proxies:
            utils.logger.warning(f"[BindingManager] 无可用代理进行自动绑定")
            return None
        
        # 选择绑定数最少的代理
        best_proxy = None
        min_bindings = float('inf')
        
        for proxy in proxies:
            binding_count = await self._binding_store.count_bindings_by_proxy(proxy.proxy_id)
            if binding_count < self._max_bindings_per_proxy and binding_count < min_bindings:
                min_bindings = binding_count
                best_proxy = proxy
        
        if not best_proxy:
            # 所有代理都达到最大绑定数，选择第一个
            best_proxy = proxies[0]
        
        return await self.bind(account_id, platform, best_proxy.proxy_id)
    
    async def _find_best_proxy(
        self,
        old_proxy: Optional[PersistedProxy],
        exclude_ids: List[str],
    ) -> Optional[PersistedProxy]:
        """
        寻找最佳代理
        
        优先选择:
        1. 同地区代理
        2. 绑定数少的代理
        3. 质量分高的代理
        """
        # 获取可用代理
        proxies = await self._proxy_store.get_available_proxies(
            exclude_proxy_ids=exclude_ids,
            limit=20,
        )
        
        if not proxies:
            return None
        
        # 如果不需要优先相似地区或没有原代理信息
        if not self._prefer_similar_region or not old_proxy:
            return await self._select_by_binding_count(proxies)
        
        # 计算地区相似度
        old_region = ProxyRegionInfo(
            proxy_id=old_proxy.proxy_id,
            country=old_proxy.country,
            province=old_proxy.province,
            city=old_proxy.city,
            isp=old_proxy.isp,
        )
        
        scored_proxies = []
        for proxy in proxies:
            new_region = ProxyRegionInfo(
                proxy_id=proxy.proxy_id,
                country=proxy.country,
                province=proxy.province,
                city=proxy.city,
                isp=proxy.isp,
            )
            similarity = old_region.similarity_score(new_region)
            binding_count = await self._binding_store.count_bindings_by_proxy(proxy.proxy_id)
            
            # 综合得分：相似度 + (1 - 绑定比例)
            score = similarity * 0.6 + (1 - binding_count / self._max_bindings_per_proxy) * 0.4
            scored_proxies.append((proxy, score))
        
        # 按得分排序
        scored_proxies.sort(key=lambda x: x[1], reverse=True)
        return scored_proxies[0][0]
    
    async def _select_by_binding_count(
        self,
        proxies: List[PersistedProxy],
    ) -> Optional[PersistedProxy]:
        """按绑定数选择代理"""
        best_proxy = None
        min_bindings = float('inf')
        
        for proxy in proxies:
            binding_count = await self._binding_store.count_bindings_by_proxy(proxy.proxy_id)
            if binding_count < min_bindings:
                min_bindings = binding_count
                best_proxy = proxy
        
        return best_proxy
    
    async def mark_proxy_failed(
        self,
        account_id: str,
        platform: str,
        error_type: Optional[str] = None,
    ) -> None:
        """
        标记代理失败
        
        连续失败可能触发自动重绑
        
        Args:
            account_id: 账号ID
            platform: 平台
            error_type: 错误类型
        """
        binding = await self.get_binding(account_id, platform)
        if not binding:
            return
        
        # 这里可以记录失败次数，触发自动重绑
        # 实际的质量指标更新由QualityEvaluator处理
        utils.logger.warning(
            f"[BindingManager] 账号 {account_id}@{platform} 代理请求失败: {error_type}"
        )
    
    async def verify_binding(self, account_id: str, platform: str) -> bool:
        """
        验证绑定的代理是否仍然可用
        
        Args:
            account_id: 账号ID
            platform: 平台
            
        Returns:
            是否可用
        """
        binding = await self.get_binding(account_id, platform)
        if not binding:
            return False
        
        proxy = await self._proxy_store.get_proxy(binding.proxy_id)
        if not proxy or not proxy.is_active:
            return False
        
        ip_info = proxy.to_ip_info_model()
        return not ip_info.is_expired()
    
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccountProxyBinding]:
        """获取所有绑定"""
        return await self._binding_store.get_all_bindings(
            platform=platform,
            status=status,
            limit=limit,
            offset=offset,
        )
    
    async def get_binding_history(
        self,
        account_id: str,
        platform: str,
        limit: int = 50,
    ) -> List[Dict]:
        """获取绑定历史"""
        return await self._binding_store.get_binding_history(
            account_id=account_id,
            platform=platform,
            limit=limit,
        )
    
    async def count_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计绑定数量"""
        return await self._binding_store.count_bindings(
            platform=platform,
            status=status,
        )
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._binding_cache.clear()

