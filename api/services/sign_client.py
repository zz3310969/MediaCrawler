"""
签名服务客户端
用于调用 SignSrv 获取请求签名
"""
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SignConfig:
    """签名服务配置"""
    enabled: bool = False
    url: str = "http://localhost:8989"
    timeout: float = 10.0
    retry_count: int = 2


class SignError(Exception):
    """签名错误"""
    pass


class SignClient:
    """签名服务客户端"""
    
    def __init__(self, config: SignConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self._config.url,
            timeout=self._config.timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    @property
    def enabled(self) -> bool:
        return self._config.enabled
    
    @property
    def url(self) -> str:
        return self._config.url
    
    async def _request(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送签名请求"""
        if not self._client:
            raise SignError("Client not initialized")
        
        for attempt in range(self._config.retry_count + 1):
            try:
                response = await self._client.post(path, json=data)
                response.raise_for_status()
                
                result = response.json()
                if result.get("code") != 0:
                    raise SignError(f"Sign error: {result.get('msg')}")
                
                return result.get("data", {})
            
            except httpx.HTTPError as e:
                logger.warning(f"Sign request failed (attempt {attempt + 1}): {e}")
                if attempt == self._config.retry_count:
                    raise SignError(f"Sign request failed after {attempt + 1} attempts: {e}")
        
        raise SignError("Sign request failed")
    
    # ========== 平台签名方法 ==========
    
    async def sign_xhs(
        self,
        uri: str,
        data: str = "",
        cookies: str = "",
        a1: str = ""
    ) -> Dict[str, str]:
        """
        小红书签名
        
        Args:
            uri: 请求 URI，如 "/api/sns/web/v1/search/notes"
            data: POST body（可选）
            cookies: 登录态 cookie
            a1: a1 参数
        
        Returns:
            {"x-s": "...", "x-t": "...", "x-s-common": "..."}
        """
        return await self._request("/api/xhs/sign", {
            "uri": uri,
            "data": data,
            "cookies": cookies,
            "a1": a1
        })
    
    async def sign_douyin(
        self,
        url: str,
        user_agent: str = ""
    ) -> Dict[str, str]:
        """
        抖音签名
        
        Args:
            url: 完整请求 URL
            user_agent: User-Agent
        
        Returns:
            {"a_bogus": "...", "ttwid": "..."}
        """
        return await self._request("/api/douyin/sign", {
            "url": url,
            "user_agent": user_agent
        })
    
    async def sign_bilibili(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        B站签名
        
        Args:
            params: 请求参数
        
        Returns:
            {"w_rid": "...", "wts": "..."}
        """
        return await self._request("/api/bilibili/sign", {
            "params": params
        })
    
    async def sign_zhihu(
        self,
        url: str,
        cookies: str = ""
    ) -> Dict[str, str]:
        """
        知乎签名
        
        Args:
            url: 请求 URL
            cookies: 登录态 cookie
        
        Returns:
            {"x-zse-93": "...", "x-zse-96": "..."}
        """
        return await self._request("/api/zhihu/sign", {
            "url": url,
            "cookies": cookies
        })
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._client:
                return False
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False


# ========== 全局实例管理 ==========

_sign_client: Optional[SignClient] = None


def get_sign_client() -> Optional[SignClient]:
    """获取签名客户端实例"""
    return _sign_client


async def init_sign_client(config: SignConfig) -> SignClient:
    """初始化签名客户端"""
    global _sign_client
    _sign_client = SignClient(config)
    await _sign_client.__aenter__()
    
    # 健康检查
    if config.enabled:
        is_healthy = await _sign_client.health_check()
        if is_healthy:
            logger.info(f"Sign client initialized, connected to {config.url}")
        else:
            logger.warning(f"Sign server at {config.url} is not available")
    
    return _sign_client


async def close_sign_client():
    """关闭签名客户端"""
    global _sign_client
    if _sign_client:
        await _sign_client.__aexit__(None, None, None)
        _sign_client = None
        logger.info("Sign client closed")


def is_sign_server_enabled() -> bool:
    """检查签名服务是否启用"""
    return _sign_client is not None and _sign_client.enabled

