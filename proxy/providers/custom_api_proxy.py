# -*- coding: utf-8 -*-
# @Desc    : 自定义API代理Provider - 允许用户配置自己的代理获取API

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from tools.utils import utils

from ..base_proxy import ProxyProvider
from ..types import IpInfoModel, ProxySource


@dataclass
class CustomApiConfig:
    """自定义API配置"""
    
    # 基本配置
    name: str                                    # 配置名称
    url: str                                     # API URL
    method: str = "GET"                          # 请求方法
    
    # 请求配置
    headers: Dict[str, str] = field(default_factory=dict)   # 请求头
    params: Dict[str, str] = field(default_factory=dict)    # 查询参数
    body: Optional[str] = None                              # 请求体
    content_type: str = "application/json"                  # 内容类型
    
    # 响应解析
    response_type: str = "json"                  # 响应类型: json | text | lines
    data_path: str = ""                          # JSON数据路径，如 "data.list"
    
    # 字段映射
    field_mapping: Dict[str, str] = field(default_factory=lambda: {
        "ip": "ip",
        "port": "port",
        "protocol": "protocol",
        "user": "user",
        "password": "password",
        "expired_time": "expire_time",
        "country": "country",
        "province": "province",
        "city": "city",
        "isp": "isp",
    })
    
    # 默认值
    default_protocol: str = "http"
    default_expired_seconds: Optional[int] = None  # 默认过期时间（秒）
    
    # 速率限制
    rate_limit_per_minute: int = 60              # 每分钟最大请求数
    min_interval_seconds: float = 1.0            # 最小请求间隔（秒）
    
    # 重试配置
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    
    def validate(self) -> bool:
        """验证配置"""
        if not self.name:
            return False
        if not self.url:
            return False
        if self.method.upper() not in ["GET", "POST"]:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "content_type": self.content_type,
            "response_type": self.response_type,
            "data_path": self.data_path,
            "field_mapping": self.field_mapping,
            "default_protocol": self.default_protocol,
            "default_expired_seconds": self.default_expired_seconds,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "min_interval_seconds": self.min_interval_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "timeout_seconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomApiConfig":
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            method=data.get("method", "GET"),
            headers=data.get("headers", {}),
            params=data.get("params", {}),
            body=data.get("body"),
            content_type=data.get("content_type", "application/json"),
            response_type=data.get("response_type", "json"),
            data_path=data.get("data_path", ""),
            field_mapping=data.get("field_mapping", {
                "ip": "ip",
                "port": "port",
                "protocol": "protocol",
                "user": "user",
                "password": "password",
            }),
            default_protocol=data.get("default_protocol", "http"),
            default_expired_seconds=data.get("default_expired_seconds"),
            rate_limit_per_minute=data.get("rate_limit_per_minute", 60),
            min_interval_seconds=data.get("min_interval_seconds", 1.0),
            retry_count=data.get("retry_count", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            timeout_seconds=data.get("timeout_seconds", 30.0),
        )


class CustomApiProxy(ProxyProvider):
    """
    自定义API代理Provider
    
    功能:
    - 支持自定义API URL和请求方式
    - 支持JSON/文本/行格式响应解析
    - 支持字段映射
    - 支持环境变量替换
    - 支持速率限制
    """
    
    # 环境变量模式
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, config: CustomApiConfig):
        """
        初始化
        
        Args:
            config: API配置
        """
        if not config.validate():
            raise ValueError("Invalid API configuration")
        
        self._config = config
        self._last_request_time: float = 0
        self._request_count_this_minute: int = 0
        self._minute_start_time: float = 0
    
    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """
        获取代理列表
        
        Args:
            num: 需要的代理数量
            
        Returns:
            代理列表
        """
        # 检查速率限制
        await self._check_rate_limit()
        
        # 替换环境变量
        url = self._replace_env_vars(self._config.url)
        headers = {k: self._replace_env_vars(v) for k, v in self._config.headers.items()}
        params = {k: self._replace_env_vars(v) for k, v in self._config.params.items()}
        
        # 添加数量参数（如果URL中有占位符）
        url = url.replace("{num}", str(num))
        params = {k: v.replace("{num}", str(num)) for k, v in params.items()}
        
        # 发起请求
        response_text = await self._make_request(url, headers, params)
        if not response_text:
            return []
        
        # 解析响应
        proxies = self._parse_response(response_text)
        
        # 限制返回数量
        return proxies[:num]
    
    def _replace_env_vars(self, text: str) -> str:
        """替换环境变量"""
        def replace(match):
            var_name = match.group(1)
            return os.environ.get(var_name, "")
        
        return self.ENV_VAR_PATTERN.sub(replace, text)
    
    async def _check_rate_limit(self) -> None:
        """检查速率限制"""
        now = time.time()
        
        # 检查最小间隔
        elapsed = now - self._last_request_time
        if elapsed < self._config.min_interval_seconds:
            await asyncio.sleep(self._config.min_interval_seconds - elapsed)
        
        # 检查每分钟限制
        if now - self._minute_start_time >= 60:
            self._request_count_this_minute = 0
            self._minute_start_time = now
        
        if self._request_count_this_minute >= self._config.rate_limit_per_minute:
            wait_time = 60 - (now - self._minute_start_time)
            if wait_time > 0:
                utils.logger.info(
                    f"[CustomApiProxy] Rate limit reached, waiting {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
                self._request_count_this_minute = 0
                self._minute_start_time = time.time()
    
    async def _make_request(
        self,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, str],
    ) -> Optional[str]:
        """发起HTTP请求"""
        for attempt in range(self._config.retry_count):
            try:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds,
                    follow_redirects=True,
                ) as client:
                    if self._config.method.upper() == "POST":
                        if self._config.content_type == "application/json":
                            response = await client.post(
                                url,
                                headers=headers,
                                params=params,
                                json=json.loads(self._config.body) if self._config.body else None,
                            )
                        else:
                            response = await client.post(
                                url,
                                headers={**headers, "Content-Type": self._config.content_type},
                                params=params,
                                content=self._config.body,
                            )
                    else:
                        response = await client.get(url, headers=headers, params=params)
                    
                    self._last_request_time = time.time()
                    self._request_count_this_minute += 1
                    
                    if response.status_code == 200:
                        return response.text
                    else:
                        utils.logger.warning(
                            f"[CustomApiProxy] API returned status {response.status_code}"
                        )
                        
            except Exception as e:
                utils.logger.warning(
                    f"[CustomApiProxy] Request failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self._config.retry_count - 1:
                    await asyncio.sleep(self._config.retry_delay_seconds)
        
        return None
    
    def _parse_response(self, text: str) -> List[IpInfoModel]:
        """解析响应"""
        if self._config.response_type == "json":
            return self._parse_json_response(text)
        elif self._config.response_type == "text":
            return self._parse_text_response(text)
        elif self._config.response_type == "lines":
            return self._parse_lines_response(text)
        else:
            utils.logger.error(f"[CustomApiProxy] Unknown response type: {self._config.response_type}")
            return []
    
    def _parse_json_response(self, text: str) -> List[IpInfoModel]:
        """解析JSON响应"""
        try:
            data = json.loads(text)
            
            # 按路径获取数据
            if self._config.data_path:
                for key in self._config.data_path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key, [])
                    elif isinstance(data, list) and key.isdigit():
                        data = data[int(key)]
                    else:
                        break
            
            # 确保是列表
            if not isinstance(data, list):
                data = [data]
            
            # 转换为代理对象
            proxies = []
            for item in data:
                proxy = self._dict_to_proxy(item)
                if proxy:
                    proxies.append(proxy)
            
            return proxies
            
        except json.JSONDecodeError as e:
            utils.logger.error(f"[CustomApiProxy] JSON parse error: {e}")
            return []
    
    def _parse_text_response(self, text: str) -> List[IpInfoModel]:
        """解析文本响应（如 ip:port 格式）"""
        proxies = []
        
        # 尝试按常见分隔符分割
        items = re.split(r'[,;\n\r]+', text.strip())
        
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            proxy = self._parse_proxy_string(item)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _parse_lines_response(self, text: str) -> List[IpInfoModel]:
        """解析行格式响应"""
        proxies = []
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            proxy = self._parse_proxy_string(line)
            if proxy:
                proxies.append(proxy)
        
        return proxies
    
    def _parse_proxy_string(self, s: str) -> Optional[IpInfoModel]:
        """解析代理字符串"""
        # 尝试URL格式: protocol://[user:password@]ip:port
        url_pattern = r"^(https?|socks[45])://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$"
        match = re.match(url_pattern, s, re.IGNORECASE)
        if match:
            protocol, user, password, ip, port = match.groups()
            return self._create_proxy(ip, int(port), protocol, user, password)
        
        # 尝试简单格式: ip:port[:user:password]
        parts = s.split(":")
        if len(parts) >= 2:
            ip = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                return None
            
            user = parts[2] if len(parts) > 2 else ""
            password = parts[3] if len(parts) > 3 else ""
            
            return self._create_proxy(ip, port, self._config.default_protocol, user, password)
        
        return None
    
    def _dict_to_proxy(self, data: Dict[str, Any]) -> Optional[IpInfoModel]:
        """将字典转换为代理对象"""
        mapping = self._config.field_mapping
        
        # 获取IP
        ip = self._get_mapped_value(data, mapping.get("ip", "ip"))
        if not ip:
            return None
        
        # 获取端口
        port_str = self._get_mapped_value(data, mapping.get("port", "port"))
        if not port_str:
            return None
        try:
            port = int(port_str)
        except (ValueError, TypeError):
            return None
        
        # 获取其他字段
        protocol = self._get_mapped_value(data, mapping.get("protocol", "protocol"))
        user = self._get_mapped_value(data, mapping.get("user", "user"))
        password = self._get_mapped_value(data, mapping.get("password", "password"))
        
        # 获取过期时间
        expired_time = self._get_mapped_value(data, mapping.get("expired_time", "expire_time"))
        
        # 获取地区信息
        country = self._get_mapped_value(data, mapping.get("country", "country"))
        province = self._get_mapped_value(data, mapping.get("province", "province"))
        city = self._get_mapped_value(data, mapping.get("city", "city"))
        isp = self._get_mapped_value(data, mapping.get("isp", "isp"))
        
        return self._create_proxy(
            ip=ip,
            port=port,
            protocol=protocol or self._config.default_protocol,
            user=user,
            password=password,
            expired_time=expired_time,
            country=country,
            province=province,
            city=city,
            isp=isp,
        )
    
    def _get_mapped_value(
        self,
        data: Dict[str, Any],
        field_path: str,
    ) -> Optional[str]:
        """获取映射的字段值（支持嵌套路径）"""
        if not field_path:
            return None
        
        value = data
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            
            if value is None:
                return None
        
        return str(value) if value is not None else None
    
    def _create_proxy(
        self,
        ip: str,
        port: int,
        protocol: str = "http",
        user: Optional[str] = None,
        password: Optional[str] = None,
        expired_time: Optional[str] = None,
        country: Optional[str] = None,
        province: Optional[str] = None,
        city: Optional[str] = None,
        isp: Optional[str] = None,
    ) -> IpInfoModel:
        """创建代理模型"""
        # 计算过期时间
        expired_ts = None
        if expired_time:
            try:
                # 尝试解析为时间戳
                expired_ts = int(float(expired_time))
            except (ValueError, TypeError):
                # 尝试解析为时间字符串
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(expired_time.replace("Z", "+00:00"))
                    expired_ts = int(dt.timestamp())
                except ValueError:
                    pass
        
        # 如果没有过期时间，使用默认值
        if expired_ts is None and self._config.default_expired_seconds:
            expired_ts = int(time.time()) + self._config.default_expired_seconds
        
        return IpInfoModel(
            ip=ip,
            port=port,
            protocol=protocol.lower().replace("://", ""),
            user=user or "",
            password=password or "",
            expired_time_ts=expired_ts,
            source=ProxySource.CUSTOM_API.value,
            country=country or "CN",
            province=province,
            city=city,
            isp=isp,
        )
    
    @property
    def config(self) -> CustomApiConfig:
        """获取配置"""
        return self._config


def new_custom_api_proxy(config: CustomApiConfig) -> CustomApiProxy:
    """
    创建自定义API代理Provider
    
    Args:
        config: API配置
        
    Returns:
        CustomApiProxy实例
    """
    return CustomApiProxy(config)


def load_custom_api_config(config_file: str) -> CustomApiConfig:
    """
    从文件加载配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        CustomApiConfig实例
    """
    import yaml
    
    with open(config_file, "r", encoding="utf-8") as f:
        if config_file.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    
    return CustomApiConfig.from_dict(data)

