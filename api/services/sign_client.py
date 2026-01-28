"""
签名服务客户端
用于调用 MediaCrawlerPro-SignSrv 获取请求签名

SignSrv API 列表:
- /signsrv/v1/xhs/sign - 小红书签名
- /signsrv/v1/xhs/update_browser_cookies - 更新 XHS 浏览器 cookies
- /signsrv/v1/douyin/sign - 抖音签名
- /signsrv/v1/bilibili/sign - B站签名
- /signsrv/v1/zhihu/sign - 知乎签名
- /signsrv/pong - 健康检查
"""
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ========== 配置 ==========

@dataclass
class SignConfig:
    """签名服务配置"""
    enabled: bool = False
    url: str = "http://localhost:8989"
    timeout: float = 10.0
    retry_count: int = 2


# ========== 响应模型 ==========

class XhsSignResult(BaseModel):
    """小红书签名结果"""
    x_s: str
    x_t: str
    x_s_common: str
    x_b3_traceid: str
    x_mns: str


class DouyinSignResult(BaseModel):
    """抖音签名结果"""
    a_bogus: str


class BilibiliSignResult(BaseModel):
    """B站签名结果"""
    wts: str
    w_rid: str


class ZhihuSignResult(BaseModel):
    """知乎签名结果"""
    x_zst_81: str
    x_zse_96: str


# ========== 异常 ==========

class SignError(Exception):
    """签名错误"""
    pass


# ========== 客户端 ==========

class SignClient:
    """签名服务客户端"""
    
    # API 路径常量
    API_XHS_SIGN = "/signsrv/v1/xhs/sign"
    API_XHS_UPDATE_COOKIES = "/signsrv/v1/xhs/update_browser_cookies"
    API_DOUYIN_SIGN = "/signsrv/v1/douyin/sign"
    API_BILIBILI_SIGN = "/signsrv/v1/bilibili/sign"
    API_ZHIHU_SIGN = "/signsrv/v1/zhihu/sign"
    API_HEALTH = "/signsrv/pong"
    
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
        """
        发送签名请求
        
        SignSrv 响应格式:
        成功: {"biz_code": 0, "msg": "OK!", "isok": true, "data": {...}}
        失败: {"biz_code": xxx, "msg": "...", "isok": false, "extra": {...}}
        """
        if not self._client:
            raise SignError("Client not initialized, use async context manager")
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self._config.retry_count + 1):
            try:
                response = await self._client.post(path, json=data)
                response.raise_for_status()
                
                result = response.json()
                
                # SignSrv 使用 biz_code 而非 code
                biz_code = result.get("biz_code")
                if biz_code != 0:
                    error_msg = result.get("msg", "Unknown error")
                    extra = result.get("extra", {})
                    raise SignError(f"Sign error (biz_code={biz_code}): {error_msg}, extra={extra}")
                
                return result.get("data", {})
            
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"Sign request HTTP error (attempt {attempt + 1}): {e}")
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Sign request failed (attempt {attempt + 1}): {e}")
            except SignError:
                raise  # 业务错误不重试
            except Exception as e:
                last_error = e
                logger.warning(f"Sign request unexpected error (attempt {attempt + 1}): {e}")
            
            if attempt < self._config.retry_count:
                continue
        
        raise SignError(f"Sign request failed after {self._config.retry_count + 1} attempts: {last_error}")
    
    # ========== 小红书签名 ==========
    
    async def sign_xhs(
        self,
        uri: str,
        data: Any = None,
        cookies: str = ""
    ) -> XhsSignResult:
        """
        小红书签名
        
        Args:
            uri: 请求 URI，如 "/api/sns/web/v1/search/notes"
            data: POST body 数据（可选）
            cookies: 登录态 cookie（必填）
        
        Returns:
            XhsSignResult 包含 x_s, x_t, x_s_common, x_b3_traceid, x_mns
        """
        result = await self._request(self.API_XHS_SIGN, {
            "uri": uri,
            "data": data,
            "cookies": cookies
        })
        return XhsSignResult(**result)
    
    async def update_xhs_cookies(self, cookies: str) -> bool:
        """
        更新小红书签名服务的浏览器 cookies
        
        Args:
            cookies: 新的 cookies 字符串
        
        Returns:
            是否更新成功
        """
        try:
            await self._request(self.API_XHS_UPDATE_COOKIES, {
                "cookies": cookies
            })
            return True
        except SignError as e:
            logger.error(f"Update XHS cookies failed: {e}")
            return False
    
    # ========== 抖音签名 ==========
    
    async def sign_douyin(
        self,
        uri: str,
        query_params: str,
        user_agent: str,
        cookies: str
    ) -> DouyinSignResult:
        """
        抖音签名
        
        Args:
            uri: 请求 URI，如 "/aweme/v1/web/search/item/"
            query_params: URL 编码后的查询参数字符串
            user_agent: User-Agent
            cookies: 登录态 cookie
        
        Returns:
            DouyinSignResult 包含 a_bogus
        """
        result = await self._request(self.API_DOUYIN_SIGN, {
            "uri": uri,
            "query_params": query_params,
            "user_agent": user_agent,
            "cookies": cookies
        })
        return DouyinSignResult(**result)
    
    # ========== B站签名 ==========
    
    async def sign_bilibili(
        self,
        req_data: Dict[str, Any],
        cookies: str
    ) -> BilibiliSignResult:
        """
        B站签名
        
        Args:
            req_data: JSON 格式的请求参数
            cookies: 登录态 cookie
        
        Returns:
            BilibiliSignResult 包含 wts, w_rid
        """
        result = await self._request(self.API_BILIBILI_SIGN, {
            "req_data": req_data,
            "cookies": cookies
        })
        return BilibiliSignResult(**result)
    
    # ========== 知乎签名 ==========
    
    async def sign_zhihu(
        self,
        uri: str,
        cookies: str
    ) -> ZhihuSignResult:
        """
        知乎签名
        
        Args:
            uri: 请求 URI
            cookies: 登录态 cookie
        
        Returns:
            ZhihuSignResult 包含 x_zst_81, x_zse_96
        """
        result = await self._request(self.API_ZHIHU_SIGN, {
            "uri": uri,
            "cookies": cookies
        })
        return ZhihuSignResult(**result)
    
    # ========== 健康检查 ==========
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            签名服务是否可用
        """
        try:
            if not self._client:
                return False
            response = await self._client.get(self.API_HEALTH)
            if response.status_code == 200:
                result = response.json()
                # SignSrv pong 响应: {"biz_code": 0, "msg": "OK!", "isok": true, "data": {"message": "pong"}}
                return result.get("biz_code") == 0
            return False
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False


# ========== 全局实例管理 ==========

_sign_client: Optional[SignClient] = None


def get_sign_client() -> Optional[SignClient]:
    """获取签名客户端实例"""
    return _sign_client


async def init_sign_client(config: SignConfig) -> SignClient:
    """
    初始化签名客户端
    
    Args:
        config: 签名服务配置
    
    Returns:
        初始化后的 SignClient 实例
    """
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
