# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import base64
import functools
import json
import random
import re
import sys
import time
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

import httpx
from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractLogin
from tools import utils

from .exception import LoginError


class WeChatLogin(AbstractLogin):
    """微信公众号登录（浏览器模式）"""

    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        cookie_str: str = "",
    ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str
        self.mp_login_url = "https://mp.weixin.qq.com/"
        self.token = None

    async def begin(self):
        """开始登录"""
        utils.logger.info(f"[WeChatLogin.begin] Begin login WeChat by {self.login_type}...")
        
        if self.login_type == "mp_qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "qrcode":
            # 微信APP扫码登录（功能受限）
            await self.login_by_mobile()
        elif self.login_type == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                f"[WeChatLogin.begin] Invalid login type: {self.login_type}. "
                "Supported types: mp_qrcode, qrcode, cookie"
            )

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        检查登录状态
        如果登录成功返回True，否则返回False
        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        
        # 检查是否有关键的登录cookie
        has_data_ticket = bool(cookie_dict.get("data_ticket"))
        has_ticket = bool(cookie_dict.get("ticket"))
        has_data_bizuin = bool(cookie_dict.get("data_bizuin"))
        
        # 只要有任一关键cookie就认为登录成功
        if has_data_ticket or has_ticket or has_data_bizuin:
            utils.logger.info("[WeChatLogin.check_login_state] Login state verified")
            return True
        
        return False

    async def login_by_qrcode(self):
        """公众号后台扫码登录"""
        utils.logger.info("[WeChatLogin.login_by_qrcode] Starting MP qrcode login...")
        
        try:
            # 访问公众号后台
            await self.context_page.goto(self.mp_login_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 查找二维码元素
            qrcode_selector = "xpath=//img[@class='qrcode lightBorder']"
            try:
                # 等待二维码出现
                await self.context_page.wait_for_selector(qrcode_selector, timeout=10000)
                utils.logger.info("[WeChatLogin.login_by_qrcode] QR code found")
            except Exception as e:
                utils.logger.error(f"[WeChatLogin.login_by_qrcode] QR code not found: {e}")
                # 尝试其他可能的选择器
                qrcode_selector = "xpath=//div[@class='login__type__container__scan']//img"
            
            # 获取二维码图片
            base64_qrcode_img = await utils.find_login_qrcode(
                self.context_page,
                selector=qrcode_selector
            )
            
            if not base64_qrcode_img:
                utils.logger.error("[WeChatLogin.login_by_qrcode] Failed to get QR code image")
                sys.exit()
            
            if not getattr(config, 'LOGIN_ONLY', False):
                partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
                asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

            # 打印二维码供 WebUI 捕获
            print(f"[QRCODE_UPDATE] {base64_qrcode_img}")
            
            utils.logger.info("[WeChatLogin.login_by_qrcode] Please scan the QR code with WeChat...")
            
            # 等待登录成功
            try:
                await self.check_login_state()
            except RetryError:
                utils.logger.error("[WeChatLogin.login_by_qrcode] Login timeout, please try again")
                sys.exit()
            
            # 等待页面跳转
            utils.logger.info("[WeChatLogin.login_by_qrcode] Login successful, waiting for redirect...")
            await asyncio.sleep(3)
            
            # 提取token
            current_url = self.context_page.url
            token = self._extract_token_from_url(current_url)
            
            if token:
                self.token = token
                utils.logger.info(f"[WeChatLogin.login_by_qrcode] Token extracted successfully")
            else:
                utils.logger.warning("[WeChatLogin.login_by_qrcode] Token not found in URL")
            
            # 获取并打印Cookie，供WebUI捕获
            cookies = await self.browser_context.cookies()
            cookie_str, _ = utils.convert_cookies(cookies)
            # 使用特殊前缀，方便 crawler_manager 解析
            # 注意：print输出会被重定向到stdout，被crawler_manager读取
            print(f"[COOKIE_UPDATE] {cookie_str}")
            if self.token:
                print(f"[TOKEN_UPDATE] {self.token}")
            
            utils.logger.info("[WeChatLogin.login_by_qrcode] Login completed successfully")
            
        except Exception as e:
            utils.logger.error(f"[WeChatLogin.login_by_qrcode] Login failed: {e}")
            raise LoginError(f"MP qrcode login failed: {e}")

    async def login_by_mobile(self):
        """微信APP扫码登录（功能受限）"""
        utils.logger.info("[WeChatLogin.login_by_mobile] WeChat APP login not implemented yet")
        utils.logger.warning("[WeChatLogin.login_by_mobile] This method has limited functionality")
        raise NotImplementedError("WeChat APP login is not implemented yet")

    async def login_by_cookies(self):
        """使用Cookie登录"""
        utils.logger.info("[WeChatLogin.login_by_cookies] Starting cookie login...")
        
        if not self.cookie_str:
            raise LoginError("Cookie string is empty")
        
        try:
            cookie_dict = utils.convert_str_cookie_to_dict(self.cookie_str)
            
            for key, value in cookie_dict.items():
                await self.browser_context.add_cookies([{
                    'name': key,
                    'value': value,
                    'domain': ".weixin.qq.com",
                    'path': "/"
                }])
            
            # 访问公众号后台验证登录
            await self.context_page.goto(self.mp_login_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 检查是否登录成功
            current_url = self.context_page.url
            if "mp.weixin.qq.com" in current_url and "token" in current_url:
                token = self._extract_token_from_url(current_url)
                if token:
                    self.token = token
                    utils.logger.info("[WeChatLogin.login_by_cookies] Cookie login successful")
                    return
            
            utils.logger.warning("[WeChatLogin.login_by_cookies] Cookie may be invalid")
            
        except Exception as e:
            utils.logger.error(f"[WeChatLogin.login_by_cookies] Cookie login failed: {e}")
            raise LoginError(f"Cookie login failed: {e}")

    def _extract_token_from_url(self, url: str) -> Optional[str]:
        """从URL中提取token"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            if 'token' in params:
                token = params['token'][0]
                return token
            
            # 尝试从URL路径中提取
            match = re.search(r'token=([^&]+)', url)
            if match:
                return match.group(1)
            
            return None
        except Exception as e:
            utils.logger.error(f"[WeChatLogin._extract_token_from_url] Failed to extract token: {e}")
            return None

    def get_token(self) -> Optional[str]:
        """获取登录后的token"""
        return self.token


class WeChatAPILogin:
    """
    微信公众号 API 登录（无浏览器模式）
    
    完全复刻 wechat-article-exporter 的登录逻辑：
    1. start_session: 获取 uuid cookie
    2. get_qrcode: 获取二维码图片
    3. poll_scan_status: 轮询扫码状态
    4. login: 获取最终 auth-key cookie 和 token
    """
    
    def __init__(self, proxy: Optional[str] = None):
        self.base_url = "https://mp.weixin.qq.com"
        self.headers = {
            "User-Agent": utils.get_user_agent(),
            "Referer": "https://mp.weixin.qq.com/",
            "Origin": "https://mp.weixin.qq.com",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.proxy = proxy
        self.client = httpx.AsyncClient(
            headers=self.headers,
            proxy=self.proxy,
            timeout=30,
            follow_redirects=False  # 不自动跟随重定向，我们需要处理 302
        )
        self.token = None
        self.cookies = {}
        
    async def begin(self):
        """执行完整登录流程"""
        try:
            utils.logger.info("[WeChatAPILogin] Starting API login process...")
            
            # 1. 开启会话
            await self.start_session()
            
            # 2. 获取二维码
            await self.get_qrcode()
            
            # 3. 轮询扫码状态
            await self.poll_scan_status()
            
            # 4. 登录完成，输出结果
            self._print_login_info()
            
        except Exception as e:
            utils.logger.error(f"[WeChatAPILogin] Login failed: {e}")
            raise LoginError(f"API login failed: {e}")
        finally:
            await self.client.aclose()
            
    async def start_session(self):
        """开启登录会话，获取 uuid cookie"""
        utils.logger.info("[WeChatAPILogin] Starting session...")
        
        timestamp = str(int(time.time() * 1000))
        random_val = str(random.randint(0, 99))
        
        # 构造 URL (实际上是一个带参数的 bizlogin 请求)
        # 注意：这里模拟的是 wechat-article-exporter 中 /api/web/login/session/[sid] 的行为
        # 实际上直接请求微信接口即可
        
        # 这一步是为了初始化 cookie jar，特别是 uuid
        # 在浏览器中访问首页会设置一些初始 cookie，这里模拟一下
        await self.client.get(self.base_url)
        
        # 开启登录流程
        # 这一步对应 bizlogin?action=startlogin
        params = {
            "action": "startlogin",
            "userlang": "zh_CN",
            "lang": "zh_CN",
            "token": "",
            "f": "json",
            "ajax": "1"
        }
        
        # POST 请求体
        data = {
            "userlang": "zh_CN",
            "redirect_url": "",
            "login_type": "3",  # 扫码登录
            "sessionid": f"{timestamp}{random_val}",
            "token": "",
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        
        url = f"{self.base_url}/cgi-bin/bizlogin"
        resp = await self.client.post(url, params=params, data=data)
        
        if resp.status_code != 200:
            raise LoginError(f"Start session failed: HTTP {resp.status_code}")
            
        json_data = resp.json()
        if json_data.get("base_resp", {}).get("ret") != 0:
             raise LoginError(f"Start session failed: {json_data}")
             
        # 检查是否获取到了 uuid cookie
        # httpx 会自动管理 cookie，我们只需确认 client.cookies 中有 uuid
        uuid = self.client.cookies.get("uuid")
        if not uuid:
            # 有时 uuid 可能在第一次访问首页时就设置了
            utils.logger.warning("[WeChatAPILogin] UUID cookie not found in response, checking jar...")
        else:
            utils.logger.info(f"[WeChatAPILogin] Session started, uuid: {uuid}")

    async def get_qrcode(self):
        """获取登录二维码"""
        utils.logger.info("[WeChatAPILogin] Fetching QR code...")
        
        timestamp = str(int(time.time() * 1000))
        params = {
            "action": "getqrcode",
            "random": timestamp
        }
        
        url = f"{self.base_url}/cgi-bin/scanloginqrcode"
        resp = await self.client.get(url, params=params)
        
        if resp.status_code != 200:
            raise LoginError(f"Get QR code failed: HTTP {resp.status_code}")
            
        # 获取图片二进制数据
        img_data = resp.content
        if not img_data:
            raise LoginError("Empty QR code image")
            
        # 转为 base64
        base64_img = base64.b64encode(img_data).decode('utf-8')
        
        if not getattr(config, 'LOGIN_ONLY', False):
            partial_show_qrcode = functools.partial(utils.show_qrcode, base64_img)
            asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)
        
        # 打印供 WebUI 捕获
        print(f"[QRCODE_UPDATE] {base64_img}")
        
        utils.logger.info("[WeChatAPILogin] QR code displayed, please scan with WeChat")

    async def poll_scan_status(self):
        """轮询扫码状态"""
        utils.logger.info("[WeChatAPILogin] Waiting for scan...")
        
        while True:
            params = {
                "action": "ask",
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
                # "random": str(int(time.time() * 1000))
            }
            
            url = f"{self.base_url}/cgi-bin/scanloginqrcode"
            
            try:
                resp = await self.client.get(url, params=params)
                if resp.status_code != 200:
                    utils.logger.warning(f"[WeChatAPILogin] Poll failed: HTTP {resp.status_code}")
                    await asyncio.sleep(2)
                    continue
                    
                data = resp.json()
                status = data.get("status")
                
                # status:
                # 0: 等待扫码
                # 1: 登录成功
                # 2: 二维码过期
                # 3: 二维码过期
                # 4: 扫码成功，等待确认
                # 6: 扫码成功，等待确认
                
                if status == 1:
                    utils.logger.info("[WeChatAPILogin] Scan confirmed, logging in...")
                    await self.finalize_login()
                    break
                    
                elif status == 4 or status == 6:
                    utils.logger.info("[WeChatAPILogin] Scanned, waiting for confirmation on phone...")
                    
                elif status == 2 or status == 3:
                    utils.logger.warning("[WeChatAPILogin] QR code expired, refreshing...")
                    await self.get_qrcode()
                    
                else:
                    # utils.logger.debug(f"[WeChatAPILogin] Waiting... status: {status}")
                    pass
                
                # 间隔
                await asyncio.sleep(2)
                
            except Exception as e:
                utils.logger.error(f"[WeChatAPILogin] Poll error: {e}")
                await asyncio.sleep(2)

    async def finalize_login(self):
        """完成登录，获取 auth-key 和 token"""
        utils.logger.info("[WeChatAPILogin] Finalizing login...")
        
        params = {
            "action": "login",
        }
        
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
        
        url = f"{self.base_url}/cgi-bin/bizlogin"
        
        # 这个请求会返回 200，内容包含 redirect_url
        # 关键是这个请求的响应头中会包含 auth-key 等重要 cookie
        resp = await self.client.post(url, params=params, data=data)
        
        if resp.status_code != 200:
             raise LoginError(f"Login finalize failed: HTTP {resp.status_code}")
             
        json_data = resp.json()
        redirect_url = json_data.get("redirect_url")
        
        if not redirect_url:
            raise LoginError(f"Login failed, no redirect_url: {json_data}")
            
        # 提取 token
        # redirect_url 示例: /cgi-bin/home?t=home/index&lang=zh_CN&token=123456789
        parsed = urlparse(f"https://mp.weixin.qq.com{redirect_url}")
        query = parse_qs(parsed.query)
        self.token = query.get("token", [""])[0]
        
        if not self.token:
            raise LoginError("Login failed, token not found in redirect_url")
            
        utils.logger.info(f"[WeChatAPILogin] Login successful! Token: {self.token}")
        
        # 收集所有 cookie
        self.cookies = dict(self.client.cookies)
        
    def _print_login_info(self):
        """输出登录信息供上层使用"""
        # 格式化 cookie 字符串
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        
        # 打印特殊标记供 crawler_manager 捕获
        print(f"[COOKIE_UPDATE] {cookie_str}")
        print(f"[TOKEN_UPDATE] {self.token}")
        
    def get_cookies_dict(self) -> Dict[str, str]:
        return self.cookies
        
    def get_token(self) -> Optional[str]:
        return self.token
