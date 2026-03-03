# -*- coding: utf-8 -*-
# @Desc    : 反爬绑定管理器 - 账号、代理、指纹三重绑定

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from .account_health import AccountHealthManager
from .fingerprint import BrowserFingerprint, FingerprintGenerator, FingerprintStore


@dataclass
class AntiDetectBinding:
    """
    反爬绑定关系

    将账号、代理、指纹三者绑定在一起，确保：
    1. 同一账号始终使用同一代理IP
    2. 同一账号始终使用同一浏览器指纹
    3. 避免频繁切换导致风控
    """

    account_id: str
    platform: str
    proxy_id: Optional[str] = None
    fingerprint_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "AntiDetectBinding":
        """从字典创建"""
        return cls(**data)


class AntiDetectBindingManager:
    """
    反爬绑定管理器

    核心功能:
    1. 账号-代理绑定：确保同一账号使用固定代理
    2. 账号-指纹绑定：确保同一账号使用固定浏览器指纹
    3. 三重绑定持久化：重启后保持绑定关系
    4. 自动生成指纹：首次使用时自动生成并绑定

    使用场景:
    - 多账号爬虫：每个账号独立的代理+指纹
    - 长期运行：避免频繁切换导致风控
    - 账号安全：降低被识别为机器人的风险
    """

    def __init__(
        self,
        storage_path: str = "data/anti_detect_bindings.json",
        fingerprint_store: Optional[FingerprintStore] = None,
        account_health_manager: Optional[AccountHealthManager] = None,
    ):
        """
        初始化绑定管理器

        Args:
            storage_path: 绑定关系存储路径
            fingerprint_store: 指纹存储器
            account_health_manager: 账号健康管理器
        """
        self.storage_path = storage_path
        self._bindings: Dict[str, AntiDetectBinding] = {}

        # 依赖模块
        self.fingerprint_store = fingerprint_store or FingerprintStore()
        self.account_health_manager = account_health_manager or AccountHealthManager()

        # 加载绑定关系
        self._load()

    def _load(self):
        """从文件加载绑定关系"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, binding_data in data.items():
                        self._bindings[key] = AntiDetectBinding.from_dict(binding_data)
            except Exception as e:
                print(f"[AntiDetectBindingManager] Failed to load bindings: {e}")

    def _save(self):
        """保存绑定关系到文件"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            data = {key: binding.to_dict() for key, binding in self._bindings.items()}
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AntiDetectBindingManager] Failed to save bindings: {e}")

    def _get_key(self, account_id: str, platform: str) -> str:
        """生成绑定键"""
        return f"{platform}:{account_id}"

    def get_binding(self, account_id: str, platform: str) -> Optional[AntiDetectBinding]:
        """
        获取账号的绑定关系

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            Optional[AntiDetectBinding]: 绑定关系，不存在则返回 None
        """
        key = self._get_key(account_id, platform)
        return self._bindings.get(key)

    def bind_proxy(self, account_id: str, platform: str, proxy_id: str):
        """
        绑定代理

        Args:
            account_id: 账号ID
            platform: 平台标识
            proxy_id: 代理ID
        """
        key = self._get_key(account_id, platform)

        if key not in self._bindings:
            self._bindings[key] = AntiDetectBinding(
                account_id=account_id, platform=platform
            )

        self._bindings[key].proxy_id = proxy_id

        # 同步到账号健康管理器
        self.account_health_manager.bind_proxy(account_id, platform, proxy_id)

        self._save()
        print(f"[AntiDetectBinding] Bound proxy {proxy_id} to {platform}:{account_id}")

    def bind_fingerprint(self, account_id: str, platform: str, fingerprint_id: str):
        """
        绑定指纹

        Args:
            account_id: 账号ID
            platform: 平台标识
            fingerprint_id: 指纹ID
        """
        key = self._get_key(account_id, platform)

        if key not in self._bindings:
            self._bindings[key] = AntiDetectBinding(
                account_id=account_id, platform=platform
            )

        self._bindings[key].fingerprint_id = fingerprint_id

        # 同步到账号健康管理器
        self.account_health_manager.bind_fingerprint(account_id, platform, fingerprint_id)

        self._save()
        print(f"[AntiDetectBinding] Bound fingerprint {fingerprint_id} to {platform}:{account_id}")

    def bind_all(
        self,
        account_id: str,
        platform: str,
        proxy_id: Optional[str] = None,
        fingerprint_id: Optional[str] = None,
    ):
        """
        一次性绑定代理和指纹

        Args:
            account_id: 账号ID
            platform: 平台标识
            proxy_id: 代理ID（可选）
            fingerprint_id: 指纹ID（可选）
        """
        key = self._get_key(account_id, platform)

        if key not in self._bindings:
            self._bindings[key] = AntiDetectBinding(
                account_id=account_id, platform=platform
            )

        if proxy_id:
            self._bindings[key].proxy_id = proxy_id
            self.account_health_manager.bind_proxy(account_id, platform, proxy_id)

        if fingerprint_id:
            self._bindings[key].fingerprint_id = fingerprint_id
            self.account_health_manager.bind_fingerprint(account_id, platform, fingerprint_id)

        self._save()
        print(f"[AntiDetectBinding] Bound proxy={proxy_id}, fingerprint={fingerprint_id} to {platform}:{account_id}")

    def get_or_create_fingerprint(
        self, account_id: str, platform: str, platform_hint: Optional[str] = None
    ) -> BrowserFingerprint:
        """
        获取或创建指纹

        如果账号已绑定指纹，则返回绑定的指纹；
        否则生成新指纹并自动绑定。

        Args:
            account_id: 账号ID
            platform: 平台标识
            platform_hint: 平台提示 ("mac", "windows", "linux")

        Returns:
            BrowserFingerprint: 浏览器指纹
        """
        binding = self.get_binding(account_id, platform)

        # 如果已绑定，尝试获取
        if binding and binding.fingerprint_id:
            fingerprint = self.fingerprint_store.get(binding.fingerprint_id)
            if fingerprint:
                print(f"[AntiDetectBinding] Using existing fingerprint {fingerprint.fingerprint_id} for {platform}:{account_id}")
                return fingerprint

        # 生成新指纹
        fingerprint = FingerprintGenerator.generate(platform_hint)
        self.fingerprint_store.save(fingerprint)

        # 自动绑定
        self.bind_fingerprint(account_id, platform, fingerprint.fingerprint_id)

        print(f"[AntiDetectBinding] Created and bound new fingerprint {fingerprint.fingerprint_id} for {platform}:{account_id}")
        return fingerprint

    def get_bound_proxy_id(self, account_id: str, platform: str) -> Optional[str]:
        """
        获取账号绑定的代理ID

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            Optional[str]: 代理ID，未绑定则返回 None
        """
        binding = self.get_binding(account_id, platform)
        return binding.proxy_id if binding else None

    def get_bound_fingerprint_id(self, account_id: str, platform: str) -> Optional[str]:
        """
        获取账号绑定的指纹ID

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            Optional[str]: 指纹ID，未绑定则返回 None
        """
        binding = self.get_binding(account_id, platform)
        return binding.fingerprint_id if binding else None

    def get_complete_binding(
        self, account_id: str, platform: str
    ) -> Tuple[Optional[str], Optional[BrowserFingerprint]]:
        """
        获取完整的绑定信息（代理ID + 指纹对象）

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            Tuple[Optional[str], Optional[BrowserFingerprint]]: (代理ID, 指纹对象)
        """
        binding = self.get_binding(account_id, platform)

        if not binding:
            return None, None

        proxy_id = binding.proxy_id
        fingerprint = None

        if binding.fingerprint_id:
            fingerprint = self.fingerprint_store.get(binding.fingerprint_id)

        return proxy_id, fingerprint

    def unbind_proxy(self, account_id: str, platform: str):
        """
        解除代理绑定

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        binding = self.get_binding(account_id, platform)
        if binding:
            binding.proxy_id = None
            self._save()
            print(f"[AntiDetectBinding] Unbound proxy from {platform}:{account_id}")

    def unbind_fingerprint(self, account_id: str, platform: str):
        """
        解除指纹绑定

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        binding = self.get_binding(account_id, platform)
        if binding:
            binding.fingerprint_id = None
            self._save()
            print(f"[AntiDetectBinding] Unbound fingerprint from {platform}:{account_id}")

    def unbind_all(self, account_id: str, platform: str):
        """
        解除所有绑定

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        key = self._get_key(account_id, platform)
        if key in self._bindings:
            del self._bindings[key]
            self._save()
            print(f"[AntiDetectBinding] Unbound all from {platform}:{account_id}")

    def list_all_bindings(self, platform: Optional[str] = None) -> Dict[str, AntiDetectBinding]:
        """
        列出所有绑定关系

        Args:
            platform: 平台标识，为空则返回所有平台

        Returns:
            Dict[str, AntiDetectBinding]: 绑定关系字典
        """
        if platform:
            return {
                key: binding
                for key, binding in self._bindings.items()
                if key.startswith(f"{platform}:")
            }
        return self._bindings.copy()

    def list_bindings(self, platform: str) -> List[AntiDetectBinding]:
        """
        列出指定平台的所有绑定（返回列表）

        Args:
            platform: 平台标识

        Returns:
            List[AntiDetectBinding]: 绑定列表
        """
        return [
            binding
            for key, binding in self._bindings.items()
            if key.startswith(f"{platform}:")
        ]

    def remove_binding(self, account_id: str, platform: str):
        """
        删除绑定（unbind_all 的别名）

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        self.unbind_all(account_id, platform)

    def get_stats(self, platform: Optional[str] = None) -> Dict:
        """
        获取统计信息

        Args:
            platform: 平台标识，为空则统计所有平台

        Returns:
            Dict: 统计数据
        """
        bindings = self.list_all_bindings(platform)

        if not bindings:
            return {
                "total_bindings": 0,
                "with_proxy": 0,
                "with_fingerprint": 0,
                "complete_bindings": 0,
            }

        with_proxy = sum(1 for b in bindings.values() if b.proxy_id)
        with_fingerprint = sum(1 for b in bindings.values() if b.fingerprint_id)
        complete = sum(1 for b in bindings.values() if b.proxy_id and b.fingerprint_id)

        return {
            "total_bindings": len(bindings),
            "with_proxy": with_proxy,
            "with_fingerprint": with_fingerprint,
            "complete_bindings": complete,
        }
