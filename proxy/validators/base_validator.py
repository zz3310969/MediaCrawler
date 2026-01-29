# -*- coding: utf-8 -*-
# @Desc    : 代理验证器基类

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..types import IpInfoModel


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    
    # 匿名性检测
    anonymity_level: str = "unknown"  # transparent | anonymous | elite
    real_ip_exposed: bool = False
    
    # 额外信息
    external_ip: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class ProxyValidator(ABC):
    """代理验证器基类"""
    
    @abstractmethod
    async def validate(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> ValidationResult:
        """
        验证代理
        
        Args:
            proxy: 代理信息
            timeout: 超时时间（秒）
            
        Returns:
            验证结果
        """
        raise NotImplementedError
    
    @abstractmethod
    async def check_anonymity(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> str:
        """
        检测代理匿名性
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
            
        Returns:
            匿名级别: transparent | anonymous | elite
        """
        raise NotImplementedError

