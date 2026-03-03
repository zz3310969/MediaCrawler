# -*- coding: utf-8 -*-
# @Desc    : 账号健康度管理

import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AccountStatus(Enum):
    """账号状态枚举"""

    ACTIVE = "active"  # 正常可用
    COOLING = "cooling"  # 冷却中（被限流）
    WARNING = "warning"  # 警告状态（风险较高）
    BANNED = "banned"  # 被封禁
    RETIRED = "retired"  # 退役（不再使用）


@dataclass
class AccountHealth:
    """
    账号健康状态

    用于跟踪账号的使用情况和风险评分
    """

    # 基本信息
    account_id: str
    platform: str

    # 状态
    status: str = AccountStatus.ACTIVE.value

    # 请求统计
    total_requests: int = 0
    failed_requests: int = 0
    captcha_count: int = 0  # 遇到验证码次数

    # 时间记录
    last_request_time: float = 0.0
    cooling_until: float = 0.0  # 冷却结束时间
    daily_reset_time: float = field(default_factory=time.time)

    # 每日统计
    daily_request_count: int = 0
    daily_failed_count: int = 0

    # 风险评分 (0-100)
    risk_score: float = 0.0

    # 绑定信息
    bound_proxy_id: Optional[str] = None  # 绑定的代理ID
    bound_fingerprint_id: Optional[str] = None  # 绑定的指纹ID

    def record_request(self, success: bool):
        """
        记录请求

        Args:
            success: 请求是否成功
        """
        now = time.time()

        # 每日重置
        if now - self.daily_reset_time > 86400:
            self.daily_request_count = 0
            self.daily_failed_count = 0
            self.daily_reset_time = now

        # 更新统计
        self.total_requests += 1
        self.daily_request_count += 1
        self.last_request_time = now

        if not success:
            self.failed_requests += 1
            self.daily_failed_count += 1

        # 更新风险评分
        self._update_risk_score()

    def record_captcha(self):
        """记录遇到验证码"""
        self.captcha_count += 1
        self.risk_score = min(100, self.risk_score + 15)
        self._maybe_cool_down()

    def record_ban(self):
        """记录被封禁"""
        self.status = AccountStatus.BANNED.value
        self.risk_score = 100

    def _update_risk_score(self):
        """更新风险评分"""
        # 基于失败率
        if self.total_requests > 10:
            fail_rate = self.failed_requests / self.total_requests
            self.risk_score = max(self.risk_score, fail_rate * 100)

        # 基于每日失败率
        if self.daily_request_count > 10:
            daily_fail_rate = self.daily_failed_count / self.daily_request_count
            self.risk_score = max(self.risk_score, daily_fail_rate * 80)

        # 基于日请求量（过高会增加风险）
        if self.daily_request_count > 500:
            self.risk_score = min(100, self.risk_score + 5)
        if self.daily_request_count > 1000:
            self.risk_score = min(100, self.risk_score + 10)

        # 基于验证码次数
        if self.captcha_count > 0:
            self.risk_score = min(100, self.risk_score + self.captcha_count * 10)

        # 风险评分自然衰减（时间越久，风险越低）
        time_since_last = time.time() - self.last_request_time
        if time_since_last > 3600:  # 1小时后开始衰减
            decay = min(20, (time_since_last - 3600) / 3600 * 5)
            self.risk_score = max(0, self.risk_score - decay)

        self._maybe_cool_down()

    def _maybe_cool_down(self):
        """根据风险评分决定是否冷却"""
        if self.status == AccountStatus.BANNED.value:
            return

        if self.risk_score > 70:
            # 高风险：冷却1小时
            self.status = AccountStatus.COOLING.value
            self.cooling_until = time.time() + 3600
        elif self.risk_score > 50:
            # 中风险：警告状态
            self.status = AccountStatus.WARNING.value
        else:
            # 低风险：恢复正常
            if self.status in [AccountStatus.COOLING.value, AccountStatus.WARNING.value]:
                self.status = AccountStatus.ACTIVE.value

    def is_available(self) -> bool:
        """
        检查账号是否可用

        Returns:
            bool: 是否可用
        """
        if self.status == AccountStatus.BANNED.value:
            return False

        if self.status == AccountStatus.RETIRED.value:
            return False

        if self.status == AccountStatus.COOLING.value:
            # 检查冷却是否结束
            if time.time() >= self.cooling_until:
                self.status = AccountStatus.ACTIVE.value
                self.risk_score = max(0, self.risk_score - 20)
                return True
            return False

        return True

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "AccountHealth":
        """从字典创建"""
        return cls(**data)


class AccountHealthManager:
    """
    账号健康管理器

    功能:
    - 管理多个账号的健康状态
    - 选择最佳可用账号
    - 持久化健康数据
    """

    def __init__(self, storage_path: str = "data/account_health.json"):
        """
        初始化管理器

        Args:
            storage_path: 存储文件路径
        """
        self.storage_path = storage_path
        self._accounts: Dict[str, AccountHealth] = {}
        self._load()

    def _load(self):
        """从文件加载健康数据"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, health_data in data.items():
                        self._accounts[key] = AccountHealth.from_dict(health_data)
            except Exception as e:
                print(f"[AccountHealthManager] Failed to load health data: {e}")

    def _save(self):
        """保存健康数据到文件"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            data = {key: health.to_dict() for key, health in self._accounts.items()}
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AccountHealthManager] Failed to save health data: {e}")

    def _get_key(self, account_id: str, platform: str) -> str:
        """生成账号键"""
        return f"{platform}:{account_id}"

    def add_account(self, account_id: str, platform: str) -> AccountHealth:
        """
        添加账号

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            AccountHealth: 账号健康对象
        """
        key = self._get_key(account_id, platform)
        if key not in self._accounts:
            self._accounts[key] = AccountHealth(account_id=account_id, platform=platform)
            self._save()
        return self._accounts[key]

    def get_account(self, account_id: str, platform: str) -> Optional[AccountHealth]:
        """
        获取账号健康对象

        Args:
            account_id: 账号ID
            platform: 平台标识

        Returns:
            Optional[AccountHealth]: 账号健康对象，不存在则返回 None
        """
        key = self._get_key(account_id, platform)
        return self._accounts.get(key)

    def get_best_account(self, platform: str) -> Optional[AccountHealth]:
        """
        获取最佳可用账号（风险最低）

        Args:
            platform: 平台标识

        Returns:
            Optional[AccountHealth]: 最佳账号，无可用账号则返回 None
        """
        now = time.time()
        candidates = []

        for key, health in self._accounts.items():
            if not key.startswith(f"{platform}:"):
                continue

            # 跳过不可用账号
            if not health.is_available():
                continue

            candidates.append(health)

        if not candidates:
            return None

        # 选择风险最低的
        return min(candidates, key=lambda a: a.risk_score)

    def get_all_accounts(self, platform: Optional[str] = None) -> List[AccountHealth]:
        """
        获取所有账号

        Args:
            platform: 平台标识，为空则返回所有平台

        Returns:
            List[AccountHealth]: 账号列表
        """
        if platform:
            return [
                health
                for key, health in self._accounts.items()
                if key.startswith(f"{platform}:")
            ]
        return list(self._accounts.values())

    def record_request(self, account_id: str, platform: str, success: bool):
        """
        记录请求

        Args:
            account_id: 账号ID
            platform: 平台标识
            success: 请求是否成功
        """
        health = self.get_account(account_id, platform)
        if not health:
            health = self.add_account(account_id, platform)

        health.record_request(success)
        self._save()

    def record_captcha(self, account_id: str, platform: str):
        """
        记录遇到验证码

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        health = self.get_account(account_id, platform)
        if not health:
            health = self.add_account(account_id, platform)

        health.record_captcha()
        self._save()

    def record_ban(self, account_id: str, platform: str):
        """
        记录被封禁

        Args:
            account_id: 账号ID
            platform: 平台标识
        """
        health = self.get_account(account_id, platform)
        if not health:
            health = self.add_account(account_id, platform)

        health.record_ban()
        self._save()

    def bind_proxy(self, account_id: str, platform: str, proxy_id: str):
        """
        绑定代理

        Args:
            account_id: 账号ID
            platform: 平台标识
            proxy_id: 代理ID
        """
        health = self.get_account(account_id, platform)
        if not health:
            health = self.add_account(account_id, platform)

        health.bound_proxy_id = proxy_id
        self._save()

    def bind_fingerprint(self, account_id: str, platform: str, fingerprint_id: str):
        """
        绑定指纹

        Args:
            account_id: 账号ID
            platform: 平台标识
            fingerprint_id: 指纹ID
        """
        health = self.get_account(account_id, platform)
        if not health:
            health = self.add_account(account_id, platform)

        health.bound_fingerprint_id = fingerprint_id
        self._save()

    def get_stats(self, platform: Optional[str] = None) -> Dict:
        """
        获取统计信息

        Args:
            platform: 平台标识，为空则统计所有平台

        Returns:
            Dict: 统计数据
        """
        accounts = self.get_all_accounts(platform)

        if not accounts:
            return {
                "total_accounts": 0,
                "active_accounts": 0,
                "cooling_accounts": 0,
                "warning_accounts": 0,
                "banned_accounts": 0,
                "avg_risk_score": 0.0,
            }

        active = sum(1 for a in accounts if a.status == AccountStatus.ACTIVE.value)
        cooling = sum(1 for a in accounts if a.status == AccountStatus.COOLING.value)
        warning = sum(1 for a in accounts if a.status == AccountStatus.WARNING.value)
        banned = sum(1 for a in accounts if a.status == AccountStatus.BANNED.value)
        avg_risk = sum(a.risk_score for a in accounts) / len(accounts)

        return {
            "total_accounts": len(accounts),
            "active_accounts": active,
            "cooling_accounts": cooling,
            "warning_accounts": warning,
            "banned_accounts": banned,
            "avg_risk_score": round(avg_risk, 2),
        }

    def list_accounts(self, platform: str) -> List[AccountHealth]:
        """
        列出指定平台的所有账号

        Args:
            platform: 平台标识

        Returns:
            List[AccountHealth]: 账号列表
        """
        return self.get_all_accounts(platform)
