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
import functools
import sys
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractLogin
from tools import utils

from .exception import LoginError


class WeChatLogin(AbstractLogin):
    """微信公众号登录"""

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
            
            # 显示二维码
            partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
            asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)
            
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

