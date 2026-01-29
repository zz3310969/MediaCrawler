# -*- coding: utf-8 -*-
# @Desc    : HTTP/HTTPS代理验证器

import time
from typing import Optional

import httpx

from tools.utils import utils

from ..types import IpInfoModel
from .base_validator import ProxyValidator, ValidationResult


class HttpValidator(ProxyValidator):
    """
    HTTP/HTTPS代理验证器
    
    支持:
    - HTTP/HTTPS代理验证
    - 匿名级别检测
    - 外网IP检测
    """
    
    # 测试URL
    DEFAULT_TEST_URLS = [
        "http://httpbin.org/ip",
        "https://api.ipify.org?format=json",
        "http://ip-api.com/json",
    ]
    
    # 匿名性检测URL
    ANONYMITY_CHECK_URL = "http://httpbin.org/headers"
    
    def __init__(
        self,
        test_urls: Optional[list] = None,
    ):
        """
        初始化验证器
        
        Args:
            test_urls: 测试URL列表
        """
        self._test_urls = test_urls or self.DEFAULT_TEST_URLS
    
    async def validate(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> ValidationResult:
        """
        验证HTTP/HTTPS代理
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
            
        Returns:
            验证结果
        """
        proxy_url = proxy.to_url()
        start_time = time.time()
        
        for test_url in self._test_urls:
            try:
                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(test_url)
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        # 尝试解析外网IP
                        external_ip = None
                        try:
                            data = response.json()
                            external_ip = (
                                data.get("ip") or
                                data.get("origin") or
                                data.get("query")
                            )
                        except Exception:
                            pass
                        
                        return ValidationResult(
                            is_valid=True,
                            response_time_ms=response_time,
                            external_ip=external_ip,
                        )
                    
            except httpx.TimeoutException:
                continue
            except Exception as e:
                utils.logger.debug(f"[HttpValidator] Test failed for {test_url}: {e}")
                continue
        
        return ValidationResult(
            is_valid=False,
            response_time_ms=(time.time() - start_time) * 1000,
            error_message="All test URLs failed",
        )
    
    async def check_anonymity(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> str:
        """
        检测代理匿名性
        
        匿名级别:
        - transparent: 透明代理，暴露真实IP
        - anonymous: 匿名代理，不暴露真实IP但表明是代理
        - elite: 高匿代理，完全隐藏代理特征
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
            
        Returns:
            匿名级别
        """
        proxy_url = proxy.to_url()
        
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=timeout,
            ) as client:
                response = await client.get(self.ANONYMITY_CHECK_URL)
                
                if response.status_code != 200:
                    return "unknown"
                
                data = response.json()
                headers = data.get("headers", {})
                
                # 检测代理相关头部
                proxy_headers = [
                    "X-Forwarded-For",
                    "X-Real-Ip",
                    "X-Proxy-Id",
                    "Via",
                    "Proxy-Connection",
                    "X-Forwarded-Host",
                    "X-Forwarded-Proto",
                ]
                
                found_proxy_headers = []
                for header in proxy_headers:
                    if header in headers or header.lower() in [h.lower() for h in headers]:
                        found_proxy_headers.append(header)
                
                if not found_proxy_headers:
                    return "elite"
                
                # 检查是否暴露真实IP
                x_forwarded_for = headers.get("X-Forwarded-For", "")
                if x_forwarded_for:
                    # 如果包含多个IP，可能暴露了真实IP
                    ips = [ip.strip() for ip in x_forwarded_for.split(",")]
                    if len(ips) > 1:
                        return "transparent"
                
                return "anonymous"
                
        except Exception as e:
            utils.logger.debug(f"[HttpValidator] Anonymity check failed: {e}")
            return "unknown"
    
    async def get_external_ip(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> Optional[str]:
        """
        获取代理的外网IP
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
            
        Returns:
            外网IP地址
        """
        result = await self.validate(proxy, timeout)
        return result.external_ip if result.is_valid else None


async def validate_http_proxy(
    proxy: IpInfoModel,
    timeout: float = 10.0,
) -> ValidationResult:
    """
    验证HTTP代理（便捷函数）
    
    Args:
        proxy: 代理信息
        timeout: 超时时间
        
    Returns:
        验证结果
    """
    validator = HttpValidator()
    return await validator.validate(proxy, timeout)

