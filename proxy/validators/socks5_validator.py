# -*- coding: utf-8 -*-
# @Desc    : SOCKS5代理验证器

import asyncio
import socket
import struct
import time
from typing import Optional, Tuple

from tools.utils import utils

from ..types import IpInfoModel
from .base_validator import ProxyValidator, ValidationResult


class Socks5Validator(ProxyValidator):
    """
    SOCKS5代理验证器
    
    支持:
    - SOCKS5连接验证
    - 用户名/密码认证
    - 匿名级别检测
    """
    
    # SOCKS5协议常量
    SOCKS5_VERSION = 0x05
    
    # 认证方法
    AUTH_NONE = 0x00
    AUTH_USER_PASS = 0x02
    AUTH_NO_ACCEPTABLE = 0xFF
    
    # 命令
    CMD_CONNECT = 0x01
    
    # 地址类型
    ATYPE_IPV4 = 0x01
    ATYPE_DOMAIN = 0x03
    ATYPE_IPV6 = 0x04
    
    # 响应状态
    REPLY_SUCCESS = 0x00
    
    # 测试URL
    DEFAULT_TEST_HOST = "www.google.com"
    DEFAULT_TEST_PORT = 80
    
    def __init__(
        self,
        test_host: str = DEFAULT_TEST_HOST,
        test_port: int = DEFAULT_TEST_PORT,
    ):
        """
        初始化验证器
        
        Args:
            test_host: 测试目标主机
            test_port: 测试目标端口
        """
        self._test_host = test_host
        self._test_port = test_port
    
    async def validate(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> ValidationResult:
        """
        验证SOCKS5代理
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
            
        Returns:
            验证结果
        """
        start_time = time.time()
        
        try:
            # 创建socket连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(proxy.ip, proxy.port),
                timeout=timeout,
            )
            
            try:
                # 进行SOCKS5握手
                success, error = await self._socks5_handshake(
                    reader, writer, proxy, timeout
                )
                
                if not success:
                    return ValidationResult(
                        is_valid=False,
                        error_message=error,
                    )
                
                # 连接测试目标
                success, error = await self._connect_target(
                    reader, writer, self._test_host, self._test_port, timeout
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if success:
                    return ValidationResult(
                        is_valid=True,
                        response_time_ms=response_time,
                    )
                else:
                    return ValidationResult(
                        is_valid=False,
                        response_time_ms=response_time,
                        error_message=error,
                    )
                    
            finally:
                writer.close()
                await writer.wait_closed()
                
        except asyncio.TimeoutError:
            return ValidationResult(
                is_valid=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Connection timeout",
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )
    
    async def _socks5_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        proxy: IpInfoModel,
        timeout: float,
    ) -> Tuple[bool, Optional[str]]:
        """
        SOCKS5握手
        
        Returns:
            (成功标志, 错误信息)
        """
        # 确定认证方法
        if proxy.user and proxy.password:
            auth_methods = [self.AUTH_NONE, self.AUTH_USER_PASS]
        else:
            auth_methods = [self.AUTH_NONE]
        
        # 发送问候消息
        greeting = struct.pack(
            f"!BB{len(auth_methods)}B",
            self.SOCKS5_VERSION,
            len(auth_methods),
            *auth_methods,
        )
        writer.write(greeting)
        await writer.drain()
        
        # 读取服务器响应
        try:
            response = await asyncio.wait_for(reader.read(2), timeout=timeout)
        except asyncio.TimeoutError:
            return False, "Handshake timeout"
        
        if len(response) < 2:
            return False, "Invalid handshake response"
        
        version, chosen_method = struct.unpack("!BB", response)
        
        if version != self.SOCKS5_VERSION:
            return False, f"Invalid SOCKS version: {version}"
        
        if chosen_method == self.AUTH_NO_ACCEPTABLE:
            return False, "No acceptable authentication method"
        
        # 处理认证
        if chosen_method == self.AUTH_USER_PASS:
            if not proxy.user or not proxy.password:
                return False, "Authentication required but no credentials provided"
            
            auth_success, auth_error = await self._authenticate(
                reader, writer, proxy.user, proxy.password, timeout
            )
            if not auth_success:
                return False, auth_error
        
        return True, None
    
    async def _authenticate(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        username: str,
        password: str,
        timeout: float,
    ) -> Tuple[bool, Optional[str]]:
        """用户名/密码认证"""
        # 认证版本1
        user_bytes = username.encode("utf-8")
        pass_bytes = password.encode("utf-8")
        
        auth_request = struct.pack(
            f"!BB{len(user_bytes)}sB{len(pass_bytes)}s",
            0x01,  # 认证版本
            len(user_bytes),
            user_bytes,
            len(pass_bytes),
            pass_bytes,
        )
        writer.write(auth_request)
        await writer.drain()
        
        # 读取认证响应
        try:
            response = await asyncio.wait_for(reader.read(2), timeout=timeout)
        except asyncio.TimeoutError:
            return False, "Authentication timeout"
        
        if len(response) < 2:
            return False, "Invalid authentication response"
        
        version, status = struct.unpack("!BB", response)
        
        if status != 0x00:
            return False, "Authentication failed"
        
        return True, None
    
    async def _connect_target(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        timeout: float,
    ) -> Tuple[bool, Optional[str]]:
        """连接目标主机"""
        # 构建连接请求
        host_bytes = host.encode("utf-8")
        connect_request = struct.pack(
            f"!BBBB{len(host_bytes) + 1}sH",
            self.SOCKS5_VERSION,
            self.CMD_CONNECT,
            0x00,  # 保留
            self.ATYPE_DOMAIN,
            struct.pack(f"!B{len(host_bytes)}s", len(host_bytes), host_bytes),
            port,
        )
        writer.write(connect_request)
        await writer.drain()
        
        # 读取响应
        try:
            response = await asyncio.wait_for(reader.read(4), timeout=timeout)
        except asyncio.TimeoutError:
            return False, "Connect timeout"
        
        if len(response) < 4:
            return False, "Invalid connect response"
        
        version, reply, _, atype = struct.unpack("!BBBB", response)
        
        if version != self.SOCKS5_VERSION:
            return False, f"Invalid SOCKS version in reply: {version}"
        
        if reply != self.REPLY_SUCCESS:
            error_messages = {
                0x01: "General SOCKS server failure",
                0x02: "Connection not allowed by ruleset",
                0x03: "Network unreachable",
                0x04: "Host unreachable",
                0x05: "Connection refused",
                0x06: "TTL expired",
                0x07: "Command not supported",
                0x08: "Address type not supported",
            }
            return False, error_messages.get(reply, f"Unknown error: {reply}")
        
        # 读取绑定地址（跳过）
        try:
            if atype == self.ATYPE_IPV4:
                await asyncio.wait_for(reader.read(4 + 2), timeout=timeout)
            elif atype == self.ATYPE_DOMAIN:
                domain_len_bytes = await asyncio.wait_for(reader.read(1), timeout=timeout)
                domain_len = struct.unpack("!B", domain_len_bytes)[0]
                await asyncio.wait_for(reader.read(domain_len + 2), timeout=timeout)
            elif atype == self.ATYPE_IPV6:
                await asyncio.wait_for(reader.read(16 + 2), timeout=timeout)
        except asyncio.TimeoutError:
            return False, "Timeout reading bind address"
        
        return True, None
    
    async def check_anonymity(
        self,
        proxy: IpInfoModel,
        timeout: float = 10.0,
    ) -> str:
        """
        检测SOCKS5代理匿名性
        
        SOCKS5代理通常是高匿名的（elite），因为协议本身不传递客户端信息
        """
        # SOCKS5代理默认是高匿名
        # 可以通过httpbin等服务进一步验证
        result = await self.validate(proxy, timeout)
        
        if result.is_valid:
            return "elite"
        return "unknown"


async def validate_socks5_proxy(
    proxy: IpInfoModel,
    timeout: float = 10.0,
    test_host: str = "www.google.com",
    test_port: int = 80,
) -> ValidationResult:
    """
    验证SOCKS5代理（便捷函数）
    
    Args:
        proxy: 代理信息
        timeout: 超时时间
        test_host: 测试目标主机
        test_port: 测试目标端口
        
    Returns:
        验证结果
    """
    validator = Socks5Validator(test_host=test_host, test_port=test_port)
    return await validator.validate(proxy, timeout)

