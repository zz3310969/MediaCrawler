# -*- coding: utf-8 -*-
import asyncio
import time
import random
import base64
import json
from typing import Optional, Dict, Tuple, Union
import httpx

from tools import utils
from tools.utils import logger

class WeChatAPILogin:
    """
    微信公众号纯API模拟登录
    
    无需浏览器环境，通过模拟 API 请求实现扫码登录。
    流程：
    1. start_session: 获取 uuid
    2. get_qrcode: 获取二维码
    3. poll_status: 轮询扫码状态
    4. login: 登录并获取 token/cookie
    """
    
    def __init__(self):
        self.base_url = "https://mp.weixin.qq.com"
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://mp.weixin.qq.com/",
                "Origin": "https://mp.weixin.qq.com",
                "Host": "mp.weixin.qq.com",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=30,
            follow_redirects=True
        )
        self.token = None
        self.cookies: Dict[str, str] = {}

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    async def start_session(self) -> bool:
        """
        步骤1: 开启登录会话，获取 uuid
        """
        logger.info("[WeChatAPILogin.start_session] Starting login session...")
        
        # 生成随机 session id
        sid = f"{int(time.time() * 1000)}{random.randint(0, 99)}"
        
        url = f"{self.base_url}/cgi-bin/bizlogin?action=startlogin"
        data = {
            "userlang": "zh_CN",
            "redirect_url": "",
            "login_type": "3",
            "sessionid": sid,
            "token": "",
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        
        try:
            resp = await self.client.post(url, data=data)
            resp_json = resp.json()
            
            if resp_json.get("base_resp", {}).get("ret") == 0:
                # 关键是获取 Set-Cookie 中的 uuid
                # httpx 的 client 会自动管理 cookie，所以这里不需要手动提取 uuid
                # 但为了确认成功，我们可以检查一下 cookie jar
                cookies = dict(self.client.cookies)
                if "uuid" in cookies:
                    logger.info(f"[WeChatAPILogin.start_session] Session started, uuid: {cookies['uuid']}")
                    return True
                else:
                    logger.warning("[WeChatAPILogin.start_session] Session started but no uuid cookie found")
                    return False
            else:
                logger.error(f"[WeChatAPILogin.start_session] Failed: {resp_json}")
                return False
                
        except Exception as e:
            logger.error(f"[WeChatAPILogin.start_session] Error: {e}")
            return False

    async def get_qrcode(self) -> Optional[str]:
        """
        步骤2: 获取二维码
        Returns:
            Base64 encoded image string
        """
        logger.info("[WeChatAPILogin.get_qrcode] Fetching QR code...")
        
        timestamp = int(time.time() * 1000)
        url = f"{self.base_url}/cgi-bin/scanloginqrcode?action=getqrcode&random={timestamp}"
        
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200 and resp.content:
                # 转为 Base64
                b64_img = base64.b64encode(resp.content).decode('utf-8')
                return f"data:image/jpeg;base64,{b64_img}"
            else:
                logger.error(f"[WeChatAPILogin.get_qrcode] Failed to get QR code, status: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"[WeChatAPILogin.get_qrcode] Error: {e}")
            return None

    async def check_status(self) -> int:
        """
        步骤3: 检查扫码状态
        Returns:
            status code:
            0: 等待扫码
            1: 登录成功
            2: 二维码过期
            3: 二维码过期
            4: 扫码成功，等待确认
            5: 未绑定邮箱
            other: 未知错误
        """
        url = f"{self.base_url}/cgi-bin/scanloginqrcode"
        params = {
            "action": "ask",
            "token": "",
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        
        try:
            resp = await self.client.get(url, params=params)
            data = resp.json()
            
            # logger.debug(f"[WeChatAPILogin.check_status] Response: {data}")
            
            if data.get("base_resp", {}).get("ret") == 0:
                return data.get("status", -1)
            else:
                logger.warning(f"[WeChatAPILogin.check_status] API Error: {data}")
                return -1
                
        except Exception as e:
            logger.error(f"[WeChatAPILogin.check_status] Error: {e}")
            return -1

    async def login(self) -> bool:
        """
        步骤4: 正式登录
        """
        logger.info("[WeChatAPILogin.login] Finalizing login...")
        
        url = f"{self.base_url}/cgi-bin/bizlogin?action=login"
        data = {
            "userlang": "zh_CN",
            "redirect_url": "",
            "cookie_forbidden": "0",
            "cookie_cleaned": "0",
            "plugin_used": "0",
            "login_type": "3",
            "token": "",
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        
        try:
            resp = await self.client.post(url, data=data)
            data = resp.json()
            
            if data.get("base_resp", {}).get("ret") == 0:
                # 登录成功，解析跳转URL获取 token
                redirect_url = data.get("redirect_url", "")
                logger.info(f"[WeChatAPILogin.login] Login success, redirect: {redirect_url}")
                
                # 提取 Token
                # redirect_url 格式: /cgi-bin/home?t=home/index&lang=zh_CN&token=1833595738
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                if 'token' in params:
                    self.token = params['token'][0]
                
                # 更新 cookies
                self.cookies = dict(self.client.cookies)
                
                return True
            else:
                logger.error(f"[WeChatAPILogin.login] Failed: {data}")
                return False
                
        except Exception as e:
            logger.error(f"[WeChatAPILogin.login] Error: {e}")
            return False

    async def run(self) -> bool:
        """
        执行完整的登录流程
        """
        try:
            # 1. Start Session
            if not await self.start_session():
                return False
            
            # 2. Get QR Code
            qrcode_b64 = await self.get_qrcode()
            if not qrcode_b64:
                return False
            
            # 打印供 WebUI 捕获
            print(f"[QRCODE_UPDATE] {qrcode_b64}")
            
            # 本地测试时可选：utils.show_qrcode(qrcode_b64)
            
            logger.info("[WeChatAPILogin.run] Please scan the QR code with WeChat app...")
            
            # 3. Poll Status
            while True:
                status = await self.check_status()
                
                if status == 1:
                    logger.info("[WeChatAPILogin.run] Status 1: Confirmed, logging in...")
                    # 4. Login
                    if await self.login():
                        # 输出 Cookie 和 Token 供 WebUI 捕获
                        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
                        print(f"[COOKIE_UPDATE] {cookie_str}")
                        if self.token:
                            print(f"[TOKEN_UPDATE] {self.token}")
                        return True
                    else:
                        return False
                        
                elif status == 4:
                    logger.info("[WeChatAPILogin.run] Status 4: Scanned, waiting for confirmation...")
                    
                elif status in [2, 3]:
                    logger.warning("[WeChatAPILogin.run] Status 2/3: QR code expired, refreshing...")
                    # 刷新二维码
                    qrcode_b64 = await self.get_qrcode()
                    if qrcode_b64:
                        # 打印供 WebUI 捕获
                        print(f"[QRCODE_UPDATE] {qrcode_b64}")
                    else:
                        return False
                        
                elif status == 0:
                    # 等待扫码
                    pass
                else:
                    logger.warning(f"[WeChatAPILogin.run] Unknown status: {status}")
                
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"[WeChatAPILogin.run] Exception: {e}")
            return False
        finally:
            await self.close()

    def get_results(self) -> Tuple[Optional[str], Dict[str, str]]:
        """获取登录结果: (token, cookies)"""
        return self.token, self.cookies
