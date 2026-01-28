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

import json
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed

import config
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool

from .exception import DataFetchError, TokenExpiredError, RateLimitError


class WeChatClient(ProxyRefreshMixin):
    """微信公众号API客户端"""

    def __init__(
        self,
        timeout=60,
        proxy=None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._mp_host = "https://mp.weixin.qq.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.token = None  # 公众号后台token
        # Initialize proxy pool
        self.init_proxy_pool(proxy_ip_pool)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def request(self, method, url, **kwargs) -> Union[Response, Dict]:
        """发送HTTP请求"""
        # Check if proxy is expired before each request
        await self._refresh_proxy_if_expired()

        enable_return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if enable_return_response:
            return response

        # 检查响应状态码
        if response.status_code != 200:
            utils.logger.error(f"[WeChatClient.request] request {method}:{url} err code: {response.status_code}")
            raise DataFetchError(f"HTTP error: {response.status_code}")

        try:
            data: Dict = response.json()
        except json.decoder.JSONDecodeError:
            utils.logger.error(f"[WeChatClient.request] Failed to parse JSON response: {response.text[:200]}")
            raise DataFetchError("Invalid JSON response")

        # 检查微信API响应
        base_resp = data.get("base_resp", {})
        ret_code = base_resp.get("ret", 0)
        
        if ret_code == -1:
            # Token可能过期
            utils.logger.error(f"[WeChatClient.request] Token may be expired, response: {data}")
            raise TokenExpiredError("Token expired, please login again")
        elif ret_code == 200003:
            # 频率限制
            utils.logger.error(f"[WeChatClient.request] Rate limited")
            raise RateLimitError("Too many requests, please try again later")
        elif ret_code != 0:
            err_msg = base_resp.get("err_msg", "Unknown error")
            utils.logger.error(f"[WeChatClient.request] API error: {ret_code} - {err_msg}")
            raise DataFetchError(f"API error: {err_msg}")

        return data

    async def get(self, uri: str, params=None, headers=None, **kwargs) -> Union[Response, Dict]:
        """发送GET请求"""
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?{urlencode(params)}"

        if headers is None:
            headers = self.headers
        
        return await self.request(method="GET", url=f"{self._mp_host}{final_uri}", headers=headers, **kwargs)

    async def post(self, uri: str, data: dict, headers=None, **kwargs) -> Dict:
        """发送POST请求"""
        if headers is None:
            headers = self.headers
        
        return await self.request(
            method="POST", 
            url=f"{self._mp_host}{uri}",
            data=urlencode(data),
            headers=headers,
            **kwargs
        )

    async def pong(self) -> bool:
        """检查登录状态"""
        utils.logger.info("[WeChatClient.pong] Checking WeChat MP login status...")
        try:
            # 尝试获取用户信息来验证登录状态
            if self.token:
                # 如果有token，说明是公众号后台登录
                uri = "/cgi-bin/home"
                params = {"t": "home/index", "token": self.token, "lang": "zh_CN"}
                response = await self.get(uri, params, return_response=True)
                return response.status_code == 200
            else:
                # Cookie登录验证
                return bool(self.cookie_dict.get("data_ticket") or self.cookie_dict.get("ticket"))
        except Exception as e:
            utils.logger.error(f"[WeChatClient.pong] Check login status failed: {e}")
            return False

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[List[str]] = None):
        """从浏览器上下文更新cookies"""
        if urls:
            cookies = await browser_context.cookies(urls=urls)
            utils.logger.info(f"[WeChatClient.update_cookies] Updating cookies for: {urls}")
        else:
            cookies = await browser_context.cookies()
            utils.logger.info("[WeChatClient.update_cookies] Updating all cookies")

        cookie_str, cookie_dict = utils.convert_cookies(cookies)
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict
        utils.logger.info(f"[WeChatClient.update_cookies] Cookie updated, total: {len(cookie_dict)} cookies")

    def set_token(self, token: str):
        """设置公众号后台token"""
        self.token = token
        utils.logger.info(f"[WeChatClient.set_token] Token set successfully")

    async def search_account(self, keyword: str, begin: int = 0, count: int = 5) -> Dict:
        """
        搜索公众号
        
        Args:
            keyword: 搜索关键词
            begin: 起始位置
            count: 返回数量
            
        Returns:
            公众号列表数据
        """
        if not self.token:
            raise TokenExpiredError("Token is required for searching accounts")

        uri = "/cgi-bin/searchbiz"
        params = {
            "action": "search_biz",
            "begin": begin,
            "count": count,
            "query": keyword,
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        
        utils.logger.info(f"[WeChatClient.search_account] Searching account: {keyword}")
        return await self.get(uri, params)

    async def get_account_profile(self, fakeid: str) -> Dict:
        """
        获取公众号详情（包含文章总数等信息）
        
        Args:
            fakeid: 公众号fakeid
            
        Returns:
            公众号详情数据
        """
        if not self.token:
            raise TokenExpiredError("Token is required for getting account profile")
            
        # 注意：这里使用的是 appmsgpublish 接口，虽然是获取文章列表，但返回数据中包含 app_msg_cnt
        uri = "/cgi-bin/appmsgpublish"
        params = {
            "sub": "list",
            "search_field": "null",
            "begin": 0,
            "count": 1,
            "query": "",
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        
        utils.logger.info(f"[WeChatClient.get_account_profile] Getting profile for: {fakeid}")
        return await self.get(uri, params)

    async def get_article_list(
        self,
        fakeid: str,
        begin: int = 0,
        count: int = 10,
        keyword: str = "",
    ) -> Dict:
        """
        获取公众号文章列表
        
        Args:
            fakeid: 公众号fakeid
            begin: 起始位置
            count: 返回数量
            keyword: 搜索关键词（可选）
            
        Returns:
            文章列表数据
        """
        if not self.token:
            raise TokenExpiredError("Token is required for getting article list")

        uri = "/cgi-bin/appmsgpublish"
        is_searching = bool(keyword)
        
        params = {
            "sub": "search" if is_searching else "list",
            "search_field": "7" if is_searching else "null",
            "begin": begin,
            "count": count,
            "query": keyword,
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        
        utils.logger.info(f"[WeChatClient.get_article_list] Getting articles for fakeid: {fakeid}")
        response = await self.get(uri, params)
        
        # 解析返回数据
        if response.get("base_resp", {}).get("ret") == 0:
            try:
                publish_page = json.loads(response.get("publish_page", "{}"))
                articles = []
                for item in publish_page.get("publish_list", []):
                    if item.get("publish_info"):
                        publish_info = json.loads(item["publish_info"])
                        articles.extend(publish_info.get("appmsgex", []))
                
                response["articles"] = articles
                # 提取文章总数
                response["total_count"] = publish_page.get("total_count", 0)
            except json.JSONDecodeError as e:
                utils.logger.error(f"[WeChatClient.get_article_list] Failed to parse articles: {e}")
                response["articles"] = []
                response["total_count"] = 0
        
        return response

    async def get_article_detail(
        self,
        biz: str,
        uin: str,
        key: str,
        pass_ticket: str,
        offset: int = 0,
        count: int = 10,
    ) -> Dict:
        """
        获取文章详情（通过profile_ext接口）
        
        Args:
            biz: 公众号__biz参数
            uin: 用户uin
            key: 认证key
            pass_ticket: pass_ticket
            offset: 偏移量
            count: 返回数量
            
        Returns:
            文章详情数据
        """
        uri = "/mp/profile_ext"
        params = {
            "action": "getmsg",
            "__biz": biz,
            "offset": offset,
            "count": count,
            "uin": uin,
            "key": key,
            "pass_ticket": pass_ticket,
            "f": "json",
            "is_ok": "1",
            "scene": "124",
        }
        
        utils.logger.info(f"[WeChatClient.get_article_detail] Getting article detail for biz: {biz}")
        return await self.get(uri, params)

    async def get_comments(
        self,
        biz: str,
        comment_id: str,
        uin: str,
        key: str,
        pass_ticket: str,
        buffer: str = "",
        offset: int = 1,
        limit: int = 100,
    ) -> Dict:
        """
        获取文章评论（支持分页）
        
        Args:
            biz: 公众号__biz参数
            comment_id: 评论ID
            uin: 用户uin
            key: 认证key
            pass_ticket: pass_ticket
            buffer: 分页buffer参数
            offset: 偏移量
            limit: 每页数量限制
            
        Returns:
            评论数据，包含elected_comment（精选评论）、comment（普通评论）、
            buffer（下一页的buffer）、continue_flag（是否还有更多）
        """
        uri = "/mp/appmsg_comment"
        params = {
            "action": "getcomment",
            "__biz": biz,
            "comment_id": comment_id,
            "uin": uin,
            "key": key,
            "pass_ticket": pass_ticket,
            "buffer": buffer,
            "offset": offset,
            "limit": limit,
            "f": "json",
        }
        
        utils.logger.info(f"[WeChatClient.get_comments] Getting comments (buffer={buffer[:20] if buffer else 'empty'})")
        return await self.get(uri, params)

    async def get_comment_replies(
        self,
        biz: str,
        comment_id: str,
        content_id: str,
        uin: str,
        key: str,
        pass_ticket: str,
        max_reply_id: int = 0,
        limit: int = 100,
    ) -> Dict:
        """
        获取评论的回复列表
        
        Args:
            biz: 公众号__biz参数
            comment_id: 评论ID
            content_id: 评论内容ID
            uin: 用户uin
            key: 认证key
            pass_ticket: pass_ticket
            max_reply_id: 最大回复ID（用于分页）
            limit: 每页数量限制
            
        Returns:
            回复数据
        """
        uri = "/mp/appmsg_comment"
        params = {
            "action": "getcommentreply",
            "__biz": biz,
            "comment_id": comment_id,
            "content_id": content_id,
            "uin": uin,
            "key": key,
            "pass_ticket": pass_ticket,
            "max_reply_id": max_reply_id,
            "limit": limit,
            "f": "json",
        }
        
        utils.logger.info(f"[WeChatClient.get_comment_replies] Getting replies for comment: {content_id}")
        return await self.get(uri, params)

    async def get_reading_stats(
        self,
        article_url: str,
        appmsgstat: Dict,
    ) -> Dict:
        """
        获取文章阅读量和点赞数等统计数据
        
        Args:
            article_url: 文章URL
            appmsgstat: 统计参数
            
        Returns:
            统计数据
        """
        # 这个功能需要特殊的credentials，暂时返回空实现
        utils.logger.info(f"[WeChatClient.get_reading_stats] Getting stats for: {article_url}")
        return {
            "read_num": 0,
            "like_num": 0,
            "old_like_num": 0,
        }

    async def get_article_html(self, article_url: str, with_credential: bool = False) -> Optional[str]:
        """
        获取文章HTML内容
        
        Args:
            article_url: 文章链接
            with_credential: 是否使用凭证（用于获取阅读量等数据）
            
        Returns:
            文章HTML内容
        """
        utils.logger.info(f"[WeChatClient.get_article_html] Fetching HTML for: {article_url}")
        
        try:
            # 使用与 refetch_content API 一致的 headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            # 如果需要凭证，添加特殊的cookie
            if with_credential:
                credentials = getattr(config, "WECHAT_CREDENTIALS", {})
                if credentials.get("pass_ticket") and credentials.get("uin"):
                    # 添加认证相关的cookie
                    headers["Cookie"] = f"pass_ticket={credentials['pass_ticket']}"
            
            # 使用 follow_redirects=True 跟踪重定向（与 refetch_content API 一致）
            async with httpx.AsyncClient(proxy=self.proxy, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(article_url, headers=headers)
                
                if response.status_code == 200:
                    html = response.text
                    # 验证HTML内容
                    status, comment_id = self._validate_html_content(html)
                    
                    if status == "success":
                        utils.logger.info(f"[WeChatClient.get_article_html] HTML fetched successfully")
                        return html
                    elif status == "deleted":
                        utils.logger.warning(f"[WeChatClient.get_article_html] Article deleted: {article_url}")
                        return None
                    elif status == "checking":
                        utils.logger.warning(f"[WeChatClient.get_article_html] Article under review: {article_url}")
                        return None
                    else:
                        utils.logger.error(f"[WeChatClient.get_article_html] Invalid HTML content, url: {article_url}")
                        # 打印 HTML 前 500 字符用于调试
                        utils.logger.debug(f"[WeChatClient.get_article_html] HTML preview: {html[:500] if html else 'empty'}")
                        return None
                else:
                    utils.logger.error(f"[WeChatClient.get_article_html] HTTP {response.status_code}, url: {article_url}")
                    return None
                    
        except Exception as e:
            utils.logger.error(f"[WeChatClient.get_article_html] Error: {e}")
            return None

    def _validate_html_content(self, html: str) -> tuple[str, Optional[str]]:
        """
        验证HTML内容是否有效
        
        Args:
            html: HTML内容
            
        Returns:
            (status, comment_id) - status可以是 success/deleted/checking/failure
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 检查是否有文章内容
            js_content = soup.find(id='js_content')
            if js_content:
                # 尝试提取comment_id
                comment_id = self._extract_comment_id(html)
                return ("success", comment_id)
            
            # 检查是否被删除
            layout = soup.find(id='js_fullscreen_layout_padding')
            title = soup.find('title')
            title_text = title.text if title else ""
            
            if layout or title_text == '该页面不存在':
                return ("deleted", None)
            
            # 检查是否在审核中
            if title_text == '内容审核中':
                return ("checking", None)
            
            return ("failure", None)
            
        except Exception as e:
            utils.logger.error(f"[WeChatClient._validate_html_content] Error: {e}")
            return ("failure", None)
    
    def _extract_comment_id(self, html: str) -> Optional[str]:
        """
        从HTML中提取comment_id
        
        Args:
            html: HTML内容
            
        Returns:
            comment_id或None
        """
        import re
        
        try:
            # 从HTML中提取comment_id
            # comment_id通常在appmsg_comment相关的配置中
            match = re.search(r'comment_id\s*[:=]\s*["\'](\w+)["\']', html)
            if match:
                return match.group(1)
            
            # 尝试其他模式
            match = re.search(r'var\s+comment_id\s*=\s*["\'](\w+)["\']', html)
            if match:
                return match.group(1)
                
            return None
        except Exception:
            return None
    
    async def get_album_list(
        self,
        fakeid: str,
        begin: int = 0,
        count: int = 10,
    ) -> Dict:
        """
        获取公众号的合集列表
        
        Args:
            fakeid: 公众号fakeid
            begin: 起始位置
            count: 返回数量
            
        Returns:
            合集列表数据
        """
        if not self.token:
            raise TokenExpiredError("Token is required for getting album list")
        
        uri = "/cgi-bin/appmsg"
        params = {
            "action": "list_album",
            "begin": begin,
            "count": count,
            "fakeid": fakeid,
            "type": "10",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        
        utils.logger.info(f"[WeChatClient.get_album_list] Getting albums for fakeid: {fakeid}")
        return await self.get(uri, params)
    
    async def get_album_articles(
        self,
        biz: str,
        album_id: str,
        begin_msgid: str = "",
        begin_itemidx: str = "",
        is_reverse: bool = True,
        count: int = 20,
    ) -> Dict:
        """
        获取合集中的文章列表
        
        Args:
            biz: 公众号__biz参数
            album_id: 合集ID
            begin_msgid: 起始消息ID（用于分页）
            begin_itemidx: 起始文章索引（用于分页）
            is_reverse: 是否倒序（最新的在前）
            count: 返回数量
            
        Returns:
            合集文章列表数据
        """
        uri = "/mp/appmsgalbum"
        params = {
            "action": "getalbum",
            "__biz": biz,
            "album_id": album_id,
            "count": count,
            "is_reverse": "1" if is_reverse else "0",
            "f": "json",
        }
        
        if begin_msgid:
            params["begin_msgid"] = begin_msgid
        if begin_itemidx:
            params["begin_itemidx"] = begin_itemidx
        
        utils.logger.info(f"[WeChatClient.get_album_articles] Getting album articles: {album_id}")
        return await self.get(uri, params)
    
    def extract_album_info_from_html(self, html: str) -> List[Dict]:
        """
        从文章HTML中提取所属合集信息
        
        Args:
            html: 文章HTML内容
            
        Returns:
            合集信息列表
        """
        try:
            # 查找合集信息的模式
            # 通常在 appmsg_album_infos 或类似的变量中
            pattern = r'var\s+album_list_data\s*=\s*(\[[\s\S]*?\]);'
            match = re.search(pattern, html)
            
            if match:
                try:
                    album_str = match.group(1)
                    # 清理JS语法
                    album_str = re.sub(r'(\w+):', r'"\1":', album_str)
                    album_str = album_str.replace("'", '"')
                    import json
                    albums = json.loads(album_str)
                    return albums
                except Exception:
                    pass
            
            # 尝试其他模式
            pattern2 = r'appmsg_album_infos\s*[:=]\s*(\[[\s\S]*?\])'
            match = re.search(pattern2, html)
            
            if match:
                try:
                    album_str = match.group(1)
                    album_str = re.sub(r'(\w+):', r'"\1":', album_str)
                    album_str = album_str.replace("'", '"')
                    import json
                    albums = json.loads(album_str)
                    return albums
                except Exception:
                    pass
            
            return []
            
        except Exception as e:
            utils.logger.warning(f"[WeChatClient.extract_album_info_from_html] Error: {e}")
            return []