# -*- coding: utf-8 -*-
# @Desc    : 多账号管理模块 - 账号池实现

import asyncio
import json
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import aiofiles

from tools import utils

if TYPE_CHECKING:
    from proxy.binding import AccountProxyBindingManager
    from proxy.types import IpInfoModel


class AccountStatus(Enum):
    """账号状态枚举"""
    ACTIVE = "active"           # 正常可用
    COOLING = "cooling"         # 冷却中（被限流）
    BANNED = "banned"           # 被封禁
    INVALID = "invalid"         # 登录失效
    UNUSED = "unused"           # 未使用/未登录


class ProxyBindingMode(Enum):
    """代理绑定模式"""
    AUTO = "auto"               # 自动分配
    MANUAL = "manual"           # 手动指定
    INHERIT = "inherit"         # 继承上次绑定
    NONE = "none"               # 不使用代理


@dataclass
class Account:
    """账号数据模型"""
    
    # 基本信息
    account_id: str                         # 账号唯一标识
    platform: str                           # 平台 (xhs, dy, wb, etc.)
    name: str = ""                          # 账号名称/备注
    
    # 登录凭证
    cookies: str = ""                       # Cookie字符串
    cookie_dict: Dict[str, str] = field(default_factory=dict)  # Cookie字典
    browser_data_dir: str = ""              # 浏览器数据目录 (用于持久化登录状态)
    
    # 代理配置 (可选，用于账号绑定代理)
    proxy_ip: str = ""                      # 绑定的代理IP
    proxy_port: int = 0                     # 代理端口
    proxy_user: str = ""                    # 代理用户名
    proxy_password: str = ""                # 代理密码
    
    # 代理绑定增强字段
    bound_proxy_id: Optional[str] = None    # 绑定的代理ID（来自绑定管理器）
    proxy_binding_mode: str = ProxyBindingMode.AUTO.value  # 代理绑定模式
    proxy_sticky: bool = True               # 是否粘性绑定（保持同一代理）
    
    # 状态信息
    status: str = AccountStatus.UNUSED.value  # 账号状态
    last_used_at: str = ""                  # 最后使用时间
    created_at: str = ""                    # 创建时间
    
    # 使用统计
    total_requests: int = 0                 # 总请求次数
    success_requests: int = 0               # 成功请求次数
    failed_requests: int = 0                # 失败请求次数
    
    # 限流相关
    cooling_until: str = ""                 # 冷却结束时间
    cooling_count: int = 0                  # 被限流次数
    last_error: str = ""                    # 最后一次错误
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        """从字典创建"""
        # 确保字典字段是字典类型
        if 'cookie_dict' in data and data['cookie_dict'] is None:
            data['cookie_dict'] = {}
        return cls(**data)
    
    def is_available(self) -> bool:
        """检查账号是否可用"""
        if self.status == AccountStatus.BANNED.value:
            return False
        if self.status == AccountStatus.INVALID.value:
            return False
        if self.status == AccountStatus.COOLING.value:
            # 检查冷却是否结束
            if self.cooling_until:
                cooling_end = datetime.fromisoformat(self.cooling_until)
                if datetime.now() < cooling_end:
                    return False
                # 冷却结束，恢复状态
                self.status = AccountStatus.ACTIVE.value
                self.cooling_until = ""
        return True
    
    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used_at = datetime.now().isoformat()
        self.total_requests += 1
        if self.status == AccountStatus.UNUSED.value:
            self.status = AccountStatus.ACTIVE.value
    
    def mark_success(self) -> None:
        """标记请求成功"""
        self.success_requests += 1
    
    def mark_failed(self, error: str = "") -> None:
        """标记请求失败"""
        self.failed_requests += 1
        self.last_error = error
    
    def mark_cooling(self, cooling_minutes: int = 30) -> None:
        """标记为冷却状态"""
        from datetime import timedelta
        self.status = AccountStatus.COOLING.value
        self.cooling_until = (datetime.now() + timedelta(minutes=cooling_minutes)).isoformat()
        self.cooling_count += 1
        utils.logger.warning(
            f"[Account] Account {self.account_id} marked as cooling for {cooling_minutes} minutes"
        )
    
    def mark_banned(self) -> None:
        """标记为被封禁"""
        self.status = AccountStatus.BANNED.value
        utils.logger.error(f"[Account] Account {self.account_id} marked as BANNED")
    
    def mark_invalid(self) -> None:
        """标记为登录失效"""
        self.status = AccountStatus.INVALID.value
        utils.logger.warning(f"[Account] Account {self.account_id} marked as INVALID")
    
    def get_proxy_url(self) -> Optional[str]:
        """获取代理URL"""
        if not self.proxy_ip or not self.proxy_port:
            return None
        if self.proxy_user and self.proxy_password:
            return f"http://{self.proxy_user}:{self.proxy_password}@{self.proxy_ip}:{self.proxy_port}"
        return f"http://{self.proxy_ip}:{self.proxy_port}"
    
    def get_playwright_proxy(self) -> Optional[Dict]:
        """获取Playwright格式的代理配置"""
        if not self.proxy_ip or not self.proxy_port:
            return None
        proxy = {
            "server": f"http://{self.proxy_ip}:{self.proxy_port}",
        }
        if self.proxy_user:
            proxy["username"] = self.proxy_user
        if self.proxy_password:
            proxy["password"] = self.proxy_password
        return proxy
    
    def update_proxy_from_ip_info(self, ip_info: "IpInfoModel") -> None:
        """
        从IpInfoModel更新代理配置
        
        Args:
            ip_info: 代理信息模型
        """
        self.proxy_ip = ip_info.ip
        self.proxy_port = ip_info.port
        self.proxy_user = ip_info.user
        self.proxy_password = ip_info.password
        self.bound_proxy_id = ip_info.proxy_id
    
    def clear_proxy(self) -> None:
        """清除代理配置"""
        self.proxy_ip = ""
        self.proxy_port = 0
        self.proxy_user = ""
        self.proxy_password = ""
        self.bound_proxy_id = None
    
    def has_bound_proxy(self) -> bool:
        """检查是否已绑定代理"""
        return self.bound_proxy_id is not None or (self.proxy_ip and self.proxy_port > 0)


class AccountPool:
    """账号池管理器"""
    
    def __init__(
        self,
        platform: str,
        accounts_dir: str = "./accounts",
        rotation_strategy: str = "round_robin",  # round_robin | random | least_used
        binding_manager: Optional["AccountProxyBindingManager"] = None,
    ):
        self.platform = platform
        self.accounts_dir = accounts_dir
        self.rotation_strategy = rotation_strategy
        self.accounts: List[Account] = []
        self.current_index: int = 0
        self._lock = asyncio.Lock()
        self._binding_manager = binding_manager
        self._ensure_dir_exists()
    
    def set_binding_manager(self, manager: "AccountProxyBindingManager") -> None:
        """设置代理绑定管理器"""
        self._binding_manager = manager
    
    def _ensure_dir_exists(self) -> None:
        """确保账号目录存在"""
        if not os.path.exists(self.accounts_dir):
            os.makedirs(self.accounts_dir, exist_ok=True)
    
    def _get_accounts_file(self) -> str:
        """获取账号配置文件路径"""
        return os.path.join(self.accounts_dir, f"{self.platform}_accounts.json")
    
    async def load_accounts(self) -> None:
        """从文件加载账号"""
        file_path = self._get_accounts_file()
        if not os.path.exists(file_path):
            utils.logger.info(f"[AccountPool] No accounts file found for {self.platform}")
            return
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                self.accounts = [Account.from_dict(acc) for acc in data.get('accounts', [])]
                utils.logger.info(
                    f"[AccountPool] Loaded {len(self.accounts)} accounts for {self.platform}"
                )
        except Exception as e:
            utils.logger.error(f"[AccountPool] Failed to load accounts: {e}")
    
    async def save_accounts(self) -> None:
        """保存账号到文件"""
        file_path = self._get_accounts_file()
        try:
            data = {
                'platform': self.platform,
                'updated_at': datetime.now().isoformat(),
                'accounts': [acc.to_dict() for acc in self.accounts]
            }
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            utils.logger.debug(f"[AccountPool] Saved {len(self.accounts)} accounts")
        except Exception as e:
            utils.logger.error(f"[AccountPool] Failed to save accounts: {e}")
    
    def add_account(self, account: Account) -> None:
        """添加账号"""
        # 检查是否已存在
        for existing in self.accounts:
            if existing.account_id == account.account_id:
                utils.logger.warning(
                    f"[AccountPool] Account {account.account_id} already exists, updating..."
                )
                # 更新现有账号
                idx = self.accounts.index(existing)
                self.accounts[idx] = account
                return
        self.accounts.append(account)
        utils.logger.info(f"[AccountPool] Added account: {account.account_id}")
    
    def remove_account(self, account_id: str) -> bool:
        """移除账号"""
        for acc in self.accounts:
            if acc.account_id == account_id:
                self.accounts.remove(acc)
                utils.logger.info(f"[AccountPool] Removed account: {account_id}")
                return True
        return False
    
    def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """通过ID获取账号"""
        for acc in self.accounts:
            if acc.account_id == account_id:
                return acc
        return None
    
    def get_available_accounts(self) -> List[Account]:
        """获取所有可用账号"""
        return [acc for acc in self.accounts if acc.is_available()]
    
    async def get_next_account(self) -> Optional[Account]:
        """获取下一个可用账号"""
        async with self._lock:
            available = self.get_available_accounts()
            if not available:
                utils.logger.warning("[AccountPool] No available accounts!")
                return None
            
            if self.rotation_strategy == "random":
                account = random.choice(available)
            elif self.rotation_strategy == "least_used":
                # 选择使用次数最少的账号
                account = min(available, key=lambda a: a.total_requests)
            else:  # round_robin
                # 轮询策略
                self.current_index = self.current_index % len(available)
                account = available[self.current_index]
                self.current_index += 1
            
            account.mark_used()
            await self.save_accounts()
            utils.logger.info(f"[AccountPool] Selected account: {account.account_id}")
            return account
    
    async def get_next_account_with_proxy(
        self,
        auto_bind_proxy: bool = True,
    ) -> Optional[Account]:
        """
        获取下一个可用账号，并自动绑定代理
        
        Args:
            auto_bind_proxy: 是否自动绑定代理
            
        Returns:
            带有代理信息的账号
        """
        account = await self.get_next_account()
        if not account:
            return None
        
        # 如果没有绑定管理器或不需要自动绑定，直接返回
        if not self._binding_manager or not auto_bind_proxy:
            return account
        
        # 检查绑定模式
        if account.proxy_binding_mode == ProxyBindingMode.NONE.value:
            return account
        
        # 获取或创建代理绑定
        try:
            ip_info = await self._binding_manager.get_proxy_for_account(
                account_id=account.account_id,
                platform=self.platform,
                auto_bind=True,
                auto_rebind=True,
            )
            
            if ip_info:
                account.update_proxy_from_ip_info(ip_info)
                utils.logger.info(
                    f"[AccountPool] Account {account.account_id} bound to proxy {ip_info.ip}:{ip_info.port}"
                )
        except Exception as e:
            utils.logger.warning(f"[AccountPool] Failed to bind proxy for account {account.account_id}: {e}")
        
        return account
    
    async def report_proxy_success(self, account_id: str) -> None:
        """报告代理请求成功"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_success()
            # 后续可以在这里更新代理质量指标
    
    async def report_proxy_failure(
        self,
        account_id: str,
        error: str = "",
        should_rebind: bool = False,
    ) -> Optional[Account]:
        """
        报告代理请求失败
        
        Args:
            account_id: 账号ID
            error: 错误信息
            should_rebind: 是否需要重新绑定代理
            
        Returns:
            如果重新绑定，返回更新后的账号
        """
        account = self.get_account_by_id(account_id)
        if not account:
            return None
        
        account.mark_failed(error)
        
        # 如果需要重新绑定代理
        if should_rebind and self._binding_manager and account.bound_proxy_id:
            try:
                new_binding = await self._binding_manager.rebind(
                    account_id=account.account_id,
                    platform=self.platform,
                    reason=f"代理失败: {error}",
                    exclude_proxy_ids=[account.bound_proxy_id] if account.bound_proxy_id else None,
                )
                
                if new_binding:
                    ip_info = await self._binding_manager.get_proxy_for_account(
                        account_id=account.account_id,
                        platform=self.platform,
                    )
                    if ip_info:
                        account.update_proxy_from_ip_info(ip_info)
                        utils.logger.info(
                            f"[AccountPool] Account {account_id} rebound to new proxy {ip_info.ip}:{ip_info.port}"
                        )
            except Exception as e:
                utils.logger.error(f"[AccountPool] Failed to rebind proxy: {e}")
        
        await self.save_accounts()
        return account
    
    async def report_success(self, account_id: str) -> None:
        """报告请求成功"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_success()
    
    async def report_failure(self, account_id: str, error: str = "") -> None:
        """报告请求失败"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_failed(error)
            await self.save_accounts()
    
    async def report_rate_limited(self, account_id: str, cooling_minutes: int = 30) -> None:
        """报告账号被限流"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_cooling(cooling_minutes)
            await self.save_accounts()
    
    async def report_banned(self, account_id: str) -> None:
        """报告账号被封禁"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_banned()
            await self.save_accounts()
    
    async def report_invalid(self, account_id: str) -> None:
        """报告账号登录失效"""
        account = self.get_account_by_id(account_id)
        if account:
            account.mark_invalid()
            await self.save_accounts()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取账号池统计信息"""
        available = self.get_available_accounts()
        return {
            'platform': self.platform,
            'total_accounts': len(self.accounts),
            'available_accounts': len(available),
            'active_accounts': len([a for a in self.accounts if a.status == AccountStatus.ACTIVE.value]),
            'cooling_accounts': len([a for a in self.accounts if a.status == AccountStatus.COOLING.value]),
            'banned_accounts': len([a for a in self.accounts if a.status == AccountStatus.BANNED.value]),
            'invalid_accounts': len([a for a in self.accounts if a.status == AccountStatus.INVALID.value]),
            'total_requests': sum(a.total_requests for a in self.accounts),
            'success_rate': (
                sum(a.success_requests for a in self.accounts) / 
                max(sum(a.total_requests for a in self.accounts), 1) * 100
            ),
        }
    
    def has_accounts(self) -> bool:
        """检查是否有账号"""
        return len(self.accounts) > 0
    
    def has_available_accounts(self) -> bool:
        """检查是否有可用账号"""
        return len(self.get_available_accounts()) > 0


async def create_account_pool(
    platform: str,
    accounts_dir: str = "./accounts",
    rotation_strategy: str = "round_robin",
    binding_manager: Optional["AccountProxyBindingManager"] = None,
) -> AccountPool:
    """
    创建并初始化账号池
    
    Args:
        platform: 平台名称 (xhs, dy, wb, etc.)
        accounts_dir: 账号配置目录
        rotation_strategy: 轮换策略 (round_robin | random | least_used)
        binding_manager: 代理绑定管理器（可选）
    
    Returns:
        AccountPool: 初始化好的账号池实例
    """
    pool = AccountPool(
        platform=platform,
        accounts_dir=accounts_dir,
        rotation_strategy=rotation_strategy,
        binding_manager=binding_manager,
    )
    await pool.load_accounts()
    return pool


def create_account_from_cookies(
    platform: str,
    cookies: str,
    account_id: Optional[str] = None,
    name: str = "",
    proxy_config: Optional[Dict] = None
) -> Account:
    """
    从Cookie字符串创建账号
    
    Args:
        platform: 平台名称
        cookies: Cookie字符串
        account_id: 账号ID (可选，不传则自动生成)
        name: 账号名称
        proxy_config: 代理配置 {ip, port, user, password}
    
    Returns:
        Account: 创建的账号实例
    """
    from tools.utils import convert_str_cookie_to_dict
    
    if not account_id:
        account_id = f"{platform}_{int(time.time())}_{random.randint(1000, 9999)}"
    
    cookie_dict = convert_str_cookie_to_dict(cookies)
    
    account = Account(
        account_id=account_id,
        platform=platform,
        name=name,
        cookies=cookies,
        cookie_dict=cookie_dict,
        status=AccountStatus.ACTIVE.value,
    )
    
    if proxy_config:
        account.proxy_ip = proxy_config.get('ip', '')
        account.proxy_port = proxy_config.get('port', 0)
        account.proxy_user = proxy_config.get('user', '')
        account.proxy_password = proxy_config.get('password', '')
    
    return account


def create_account_from_browser_dir(
    platform: str,
    browser_data_dir: str,
    account_id: Optional[str] = None,
    name: str = "",
    proxy_config: Optional[Dict] = None
) -> Account:
    """
    从浏览器数据目录创建账号 (用于持久化登录)
    
    Args:
        platform: 平台名称
        browser_data_dir: 浏览器数据目录路径
        account_id: 账号ID (可选)
        name: 账号名称
        proxy_config: 代理配置
    
    Returns:
        Account: 创建的账号实例
    """
    if not account_id:
        # 从目录名提取或生成
        dir_name = os.path.basename(browser_data_dir)
        account_id = f"{platform}_{dir_name}"
    
    account = Account(
        account_id=account_id,
        platform=platform,
        name=name,
        browser_data_dir=browser_data_dir,
        status=AccountStatus.ACTIVE.value,
    )
    
    if proxy_config:
        account.proxy_ip = proxy_config.get('ip', '')
        account.proxy_port = proxy_config.get('port', 0)
        account.proxy_user = proxy_config.get('user', '')
        account.proxy_password = proxy_config.get('password', '')
    
    return account

