# -*- coding: utf-8 -*-
# @Desc    : 本地文件代理Provider - 支持从文件加载静态代理列表

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from tools.utils import utils

from ..base_proxy import ProxyProvider
from ..types import IpInfoModel, ProxyProtocol, ProxySource


class LocalFileProxyError(Exception):
    """本地文件代理错误"""
    pass


class LocalFileProxy(ProxyProvider):
    """
    本地文件代理Provider
    
    支持的文件格式:
    - TXT: 每行一个代理，格式: protocol://ip:port 或 protocol://user:password@ip:port
    - JSON: 代理对象数组
    - YAML: 代理对象数组
    - CSV: 带表头的CSV文件
    
    支持文件变化监听和热重载
    """
    
    def __init__(
        self,
        file_path: str,
        auto_reload: bool = True,
        default_protocol: str = "http",
        default_expired_seconds: Optional[int] = None,
    ):
        """
        初始化本地文件代理Provider
        
        Args:
            file_path: 代理文件路径
            auto_reload: 是否自动重载文件变化
            default_protocol: 默认协议
            default_expired_seconds: 默认过期时间（秒），None表示永不过期
        """
        self.file_path = Path(file_path)
        self.auto_reload = auto_reload
        self.default_protocol = default_protocol
        self.default_expired_seconds = default_expired_seconds
        
        self._proxies: List[IpInfoModel] = []
        self._last_modified: float = 0
        self._file_hash: str = ""
        
        # 格式解析器
        self._parsers: Dict[str, Callable[[str], List[IpInfoModel]]] = {
            ".txt": self._parse_txt,
            ".json": self._parse_json,
            ".yaml": self._parse_yaml,
            ".yml": self._parse_yaml,
            ".csv": self._parse_csv,
        }
    
    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """
        获取代理列表
        
        Args:
            num: 需要的代理数量
            
        Returns:
            代理列表
        """
        # 检查是否需要重载
        if self.auto_reload:
            await self._check_and_reload()
        elif not self._proxies:
            await self._load_proxies()
        
        # 返回请求数量的代理
        return self._proxies[:num]
    
    async def _check_and_reload(self) -> None:
        """检查文件变化并重载"""
        if not self.file_path.exists():
            utils.logger.warning(f"[LocalFileProxy] 文件不存在: {self.file_path}")
            return
        
        # 检查文件修改时间
        current_mtime = os.path.getmtime(self.file_path)
        if current_mtime != self._last_modified:
            utils.logger.info(f"[LocalFileProxy] 检测到文件变化，重新加载: {self.file_path}")
            await self._load_proxies()
            self._last_modified = current_mtime
    
    async def _load_proxies(self) -> None:
        """加载代理文件"""
        if not self.file_path.exists():
            raise LocalFileProxyError(f"代理文件不存在: {self.file_path}")
        
        # 获取文件后缀
        suffix = self.file_path.suffix.lower()
        
        # 获取对应的解析器
        parser = self._parsers.get(suffix)
        if not parser:
            raise LocalFileProxyError(f"不支持的文件格式: {suffix}")
        
        # 读取文件内容
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise LocalFileProxyError(f"读取文件失败: {e}")
        
        # 解析代理
        try:
            self._proxies = parser(content)
            utils.logger.info(f"[LocalFileProxy] 成功加载 {len(self._proxies)} 个代理")
        except Exception as e:
            raise LocalFileProxyError(f"解析文件失败: {e}")
    
    def _parse_txt(self, content: str) -> List[IpInfoModel]:
        """
        解析TXT格式
        
        支持格式:
        - ip:port
        - protocol://ip:port
        - protocol://user:password@ip:port
        - ip:port:user:password
        """
        proxies = []
        lines = content.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            proxy = self._parse_proxy_line(line)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _parse_proxy_line(self, line: str) -> Optional[IpInfoModel]:
        """解析单行代理"""
        # 尝试URL格式: protocol://[user:password@]ip:port
        url_pattern = r"^(https?|socks[45])://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$"
        match = re.match(url_pattern, line, re.IGNORECASE)
        if match:
            protocol, user, password, ip, port = match.groups()
            return self._create_proxy(ip, int(port), protocol, user, password)
        
        # 尝试简单格式: ip:port[:user:password]
        parts = line.split(":")
        if len(parts) >= 2:
            ip = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                return None
            
            user = parts[2] if len(parts) > 2 else ""
            password = parts[3] if len(parts) > 3 else ""
            
            return self._create_proxy(ip, port, self.default_protocol, user, password)
        
        return None
    
    def _parse_json(self, content: str) -> List[IpInfoModel]:
        """
        解析JSON格式
        
        支持格式:
        [
            {"ip": "1.2.3.4", "port": 8080, "protocol": "http"},
            {"ip": "5.6.7.8", "port": 1080, "protocol": "socks5", "user": "u", "password": "p"}
        ]
        """
        data = json.loads(content)
        
        if not isinstance(data, list):
            data = [data]
        
        proxies = []
        for item in data:
            proxy = self._dict_to_proxy(item)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _parse_yaml(self, content: str) -> List[IpInfoModel]:
        """
        解析YAML格式
        
        支持格式:
        proxies:
          - ip: 1.2.3.4
            port: 8080
            protocol: http
          - ip: 5.6.7.8
            port: 1080
            protocol: socks5
            user: u
            password: p
        """
        data = yaml.safe_load(content)
        
        # 支持直接列表或 proxies 键
        if isinstance(data, dict):
            data = data.get("proxies", [])
        
        if not isinstance(data, list):
            data = [data]
        
        proxies = []
        for item in data:
            proxy = self._dict_to_proxy(item)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _parse_csv(self, content: str) -> List[IpInfoModel]:
        """
        解析CSV格式
        
        支持格式（需要表头）:
        ip,port,protocol,user,password
        1.2.3.4,8080,http,,
        5.6.7.8,1080,socks5,user,pass
        """
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(content))
        
        proxies = []
        for row in reader:
            proxy = self._dict_to_proxy(row)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _dict_to_proxy(self, data: Dict[str, Any]) -> Optional[IpInfoModel]:
        """将字典转换为代理模型"""
        try:
            ip = data.get("ip") or data.get("host") or data.get("address")
            port = data.get("port")
            
            if not ip or not port:
                return None
            
            return self._create_proxy(
                ip=str(ip),
                port=int(port),
                protocol=data.get("protocol", self.default_protocol),
                user=data.get("user") or data.get("username") or "",
                password=data.get("password") or data.get("pass") or "",
                country=data.get("country"),
                province=data.get("province"),
                city=data.get("city"),
                isp=data.get("isp"),
            )
        except (ValueError, TypeError):
            return None
    
    def _create_proxy(
        self,
        ip: str,
        port: int,
        protocol: str = "http",
        user: Optional[str] = None,
        password: Optional[str] = None,
        country: Optional[str] = None,
        province: Optional[str] = None,
        city: Optional[str] = None,
        isp: Optional[str] = None,
    ) -> IpInfoModel:
        """创建代理模型"""
        import time
        
        # 计算过期时间
        expired_ts = None
        if self.default_expired_seconds:
            expired_ts = int(time.time()) + self.default_expired_seconds
        
        return IpInfoModel(
            ip=ip,
            port=port,
            protocol=protocol.lower().replace("://", ""),
            user=user or "",
            password=password or "",
            expired_time_ts=expired_ts,
            source=ProxySource.LOCAL_FILE.value,
            country=country or "CN",
            province=province,
            city=city,
            isp=isp,
        )
    
    def get_all_proxies(self) -> List[IpInfoModel]:
        """获取所有已加载的代理"""
        return self._proxies.copy()
    
    @property
    def proxy_count(self) -> int:
        """获取代理数量"""
        return len(self._proxies)
    
    @property
    def loaded(self) -> bool:
        """是否已加载"""
        return len(self._proxies) > 0


def new_local_file_proxy(
    file_path: str,
    auto_reload: bool = True,
    default_protocol: str = "http",
    default_expired_seconds: Optional[int] = None,
) -> LocalFileProxy:
    """
    创建本地文件代理Provider
    
    Args:
        file_path: 代理文件路径
        auto_reload: 是否自动重载
        default_protocol: 默认协议
        default_expired_seconds: 默认过期时间
        
    Returns:
        LocalFileProxy实例
    """
    return LocalFileProxy(
        file_path=file_path,
        auto_reload=auto_reload,
        default_protocol=default_protocol,
        default_expired_seconds=default_expired_seconds,
    )

