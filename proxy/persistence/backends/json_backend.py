# -*- coding: utf-8 -*-
# @Desc    : JSON文件存储后端实现（轻量级）

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from proxy.types import PersistedProxy, AccountProxyBinding, ProxyQualityMetrics
from proxy.persistence.proxy_store import ProxyStore, BindingStore


class JsonProxyStore(ProxyStore):
    """JSON文件代理存储实现"""
    
    def __init__(self, file_path: str = "data/proxies.json"):
        self.file_path = Path(file_path)
        self._data: Dict[str, Any] = {
            "proxies": {},
            "quality_metrics": {},
        }
        self._lock = asyncio.Lock()
    
    async def init(self) -> None:
        """初始化存储"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.file_path.exists():
            async with self._lock:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
    
    async def close(self) -> None:
        """关闭连接（保存数据）"""
        await self._save()
    
    async def _save(self) -> None:
        """保存到文件"""
        async with self._lock:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
    
    async def save_proxy(self, proxy: PersistedProxy) -> None:
        """保存代理"""
        self._data["proxies"][proxy.proxy_id] = proxy.model_dump(mode="json")
        await self._save()
    
    async def save_proxies(self, proxies: List[PersistedProxy]) -> int:
        """批量保存代理"""
        count = 0
        for proxy in proxies:
            self._data["proxies"][proxy.proxy_id] = proxy.model_dump(mode="json")
            count += 1
        await self._save()
        return count
    
    async def get_proxy(self, proxy_id: str) -> Optional[PersistedProxy]:
        """获取代理"""
        data = self._data["proxies"].get(proxy_id)
        if data:
            return PersistedProxy.model_validate(data)
        return None
    
    async def get_proxy_by_address(self, ip: str, port: int) -> Optional[PersistedProxy]:
        """通过地址获取代理"""
        for data in self._data["proxies"].values():
            if data["ip"] == ip and data["port"] == port:
                return PersistedProxy.model_validate(data)
        return None
    
    async def get_all_proxies(
        self,
        source: Optional[str] = None,
        protocol: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersistedProxy]:
        """获取代理列表"""
        proxies = []
        for data in self._data["proxies"].values():
            if source is not None and data.get("source") != source:
                continue
            if protocol is not None and data.get("protocol") != protocol:
                continue
            if is_active is not None and data.get("is_active") != is_active:
                continue
            proxies.append(PersistedProxy.model_validate(data))
        
        # 按更新时间排序
        proxies.sort(key=lambda x: x.updated_at, reverse=True)
        return proxies[offset:offset + limit]
    
    async def get_available_proxies(
        self,
        protocol: Optional[str] = None,
        min_quality_score: float = 0.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """获取可用代理列表"""
        now = datetime.now()
        proxies = []
        
        for data in self._data["proxies"].values():
            if not data.get("is_active", True):
                continue
            if protocol and data.get("protocol") != protocol:
                continue
            
            # 检查过期
            expired_at = data.get("expired_at")
            if expired_at:
                if isinstance(expired_at, str):
                    expired_at = datetime.fromisoformat(expired_at)
                if expired_at < now:
                    continue
            
            proxy = PersistedProxy.model_validate(data)
            
            # 检查质量分
            metrics_data = self._data["quality_metrics"].get(proxy.proxy_id)
            if metrics_data:
                metrics = ProxyQualityMetrics.model_validate(metrics_data)
                if metrics.quality_score < min_quality_score:
                    continue
            
            proxies.append(proxy)
        
        return proxies[:limit]
    
    async def update_proxy(self, proxy: PersistedProxy) -> bool:
        """更新代理"""
        if proxy.proxy_id not in self._data["proxies"]:
            return False
        proxy.updated_at = datetime.now()
        self._data["proxies"][proxy.proxy_id] = proxy.model_dump(mode="json")
        await self._save()
        return True
    
    async def update_proxy_status(self, proxy_id: str, is_active: bool) -> bool:
        """更新代理状态"""
        if proxy_id not in self._data["proxies"]:
            return False
        self._data["proxies"][proxy_id]["is_active"] = is_active
        self._data["proxies"][proxy_id]["updated_at"] = datetime.now().isoformat()
        await self._save()
        return True
    
    async def delete_proxy(self, proxy_id: str) -> bool:
        """删除代理"""
        if proxy_id in self._data["proxies"]:
            del self._data["proxies"][proxy_id]
            # 同时删除质量指标
            self._data["quality_metrics"].pop(proxy_id, None)
            await self._save()
            return True
        return False
    
    async def delete_expired_proxies(self) -> int:
        """删除过期代理"""
        now = datetime.now()
        to_delete = []
        
        for proxy_id, data in self._data["proxies"].items():
            expired_at = data.get("expired_at")
            if expired_at:
                if isinstance(expired_at, str):
                    expired_at = datetime.fromisoformat(expired_at)
                if expired_at < now:
                    to_delete.append(proxy_id)
        
        for proxy_id in to_delete:
            del self._data["proxies"][proxy_id]
            self._data["quality_metrics"].pop(proxy_id, None)
        
        if to_delete:
            await self._save()
        return len(to_delete)
    
    async def count_proxies(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """统计代理数量"""
        count = 0
        for data in self._data["proxies"].values():
            if source is not None and data.get("source") != source:
                continue
            if is_active is not None and data.get("is_active") != is_active:
                continue
            count += 1
        return count
    
    async def save_quality_metrics(self, metrics: ProxyQualityMetrics) -> None:
        """保存质量指标"""
        self._data["quality_metrics"][metrics.proxy_id] = metrics.model_dump(mode="json")
        await self._save()
    
    async def get_quality_metrics(self, proxy_id: str) -> Optional[ProxyQualityMetrics]:
        """获取质量指标"""
        data = self._data["quality_metrics"].get(proxy_id)
        if data:
            return ProxyQualityMetrics.model_validate(data)
        return None
    
    async def get_proxies_by_quality(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """按质量分获取代理"""
        result = []
        
        for proxy_id, data in self._data["proxies"].items():
            if not data.get("is_active", True):
                continue
            
            metrics_data = self._data["quality_metrics"].get(proxy_id)
            if metrics_data:
                metrics = ProxyQualityMetrics.model_validate(metrics_data)
                score = metrics.quality_score
            else:
                score = 50  # 默认分数
            
            if min_score <= score <= max_score:
                result.append((score, PersistedProxy.model_validate(data)))
        
        # 按分数降序排序
        result.sort(key=lambda x: x[0], reverse=True)
        return [proxy for _, proxy in result[:limit]]


class JsonBindingStore(BindingStore):
    """JSON文件绑定存储实现"""
    
    def __init__(self, file_path: str = "data/bindings.json"):
        self.file_path = Path(file_path)
        self._data: Dict[str, Any] = {
            "bindings": {},
            "history": [],
        }
        self._lock = asyncio.Lock()
    
    async def init(self) -> None:
        """初始化存储"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.file_path.exists():
            async with self._lock:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
    
    async def close(self) -> None:
        """关闭连接（保存数据）"""
        await self._save()
    
    async def _save(self) -> None:
        """保存到文件"""
        async with self._lock:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
    
    def _get_key(self, account_id: str, platform: str) -> str:
        """生成唯一键"""
        return f"{platform}:{account_id}"
    
    async def save_binding(self, binding: AccountProxyBinding) -> None:
        """保存绑定"""
        key = self._get_key(binding.account_id, binding.platform)
        self._data["bindings"][key] = binding.model_dump(mode="json")
        await self._save()
    
    async def get_binding(
        self,
        account_id: str,
        platform: str,
    ) -> Optional[AccountProxyBinding]:
        """获取绑定"""
        key = self._get_key(account_id, platform)
        data = self._data["bindings"].get(key)
        if data:
            return AccountProxyBinding.model_validate(data)
        return None
    
    async def get_binding_by_id(self, binding_id: str) -> Optional[AccountProxyBinding]:
        """通过ID获取绑定"""
        for data in self._data["bindings"].values():
            if data["binding_id"] == binding_id:
                return AccountProxyBinding.model_validate(data)
        return None
    
    async def get_bindings_by_proxy(self, proxy_id: str) -> List[AccountProxyBinding]:
        """获取使用指定代理的所有绑定"""
        result = []
        for data in self._data["bindings"].values():
            if data["proxy_id"] == proxy_id:
                result.append(AccountProxyBinding.model_validate(data))
        return result
    
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccountProxyBinding]:
        """获取绑定列表"""
        result = []
        for data in self._data["bindings"].values():
            if platform is not None and data.get("platform") != platform:
                continue
            if status is not None and data.get("status") != status:
                continue
            result.append(AccountProxyBinding.model_validate(data))
        
        # 按绑定时间排序
        result.sort(key=lambda x: x.bound_at, reverse=True)
        return result[offset:offset + limit]
    
    async def update_binding(self, binding: AccountProxyBinding) -> bool:
        """更新绑定"""
        key = self._get_key(binding.account_id, binding.platform)
        if key not in self._data["bindings"]:
            return False
        self._data["bindings"][key] = binding.model_dump(mode="json")
        await self._save()
        return True
    
    async def delete_binding(self, account_id: str, platform: str) -> bool:
        """删除绑定"""
        key = self._get_key(account_id, platform)
        if key in self._data["bindings"]:
            del self._data["bindings"][key]
            await self._save()
            return True
        return False
    
    async def delete_binding_by_id(self, binding_id: str) -> bool:
        """通过ID删除绑定"""
        for key, data in list(self._data["bindings"].items()):
            if data["binding_id"] == binding_id:
                del self._data["bindings"][key]
                await self._save()
                return True
        return False
    
    async def count_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计绑定数量"""
        count = 0
        for data in self._data["bindings"].values():
            if platform is not None and data.get("platform") != platform:
                continue
            if status is not None and data.get("status") != status:
                continue
            count += 1
        return count
    
    async def count_bindings_by_proxy(self, proxy_id: str) -> int:
        """统计代理的绑定数量"""
        count = 0
        for data in self._data["bindings"].values():
            if data["proxy_id"] == proxy_id:
                count += 1
        return count
    
    async def record_rebind_history(
        self,
        binding_id: str,
        account_id: str,
        platform: str,
        old_proxy_id: Optional[str],
        new_proxy_id: str,
        action: str,
        reason: Optional[str] = None,
    ) -> None:
        """记录重绑历史"""
        self._data["history"].append({
            "binding_id": binding_id,
            "account_id": account_id,
            "platform": platform,
            "old_proxy_id": old_proxy_id,
            "new_proxy_id": new_proxy_id,
            "action": action,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        })
        # 只保留最近1000条历史
        if len(self._data["history"]) > 1000:
            self._data["history"] = self._data["history"][-1000:]
        await self._save()
