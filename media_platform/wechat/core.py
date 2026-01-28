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
import os
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from config import wechat_config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import WeChatClient
from .exception import DataFetchError
from .login import WeChatLogin


class WeChatCrawler(AbstractCrawler):
    """微信公众号爬虫"""
    
    context_page: Page
    wechat_client: WeChatClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        super().__init__()
        self.index_url = "https://mp.weixin.qq.com"
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None
        self.ip_proxy_pool = None

    async def start(self):
        """启动爬虫"""
        # 初始化进度管理器
        self._init_progress_manager()
        
        # 初始化账号池
        await self._init_account_pool("wechat")
        
        playwright_proxy_format, httpx_proxy_format = None, None
        
        # 优先使用多账号模式的代理配置
        if self._has_multi_account():
            account = await self._get_next_account()
            if account:
                playwright_proxy_format, httpx_proxy_format = self._get_account_proxy()
                if playwright_proxy_format:
                    utils.logger.info(f"[WeChatCrawler] Using account proxy: {account.proxy_ip}")
        
        # 如果没有账号代理，使用全局代理池
        if not httpx_proxy_format and config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        # 检查登录模式和类型
        login_type = config.LOGIN_TYPE
        login_mode = getattr(wechat_config, "LOGIN_MODE", "browser")
        
        # 尝试使用账号 Cookie
        if self._current_account and self._current_account.cookies:
            login_type = "cookie"
            utils.logger.info(f"[WeChatCrawler] Using account cookies for login")

        # 判断是否可以使用 API 登录
        use_api_login = (login_mode == "api" and login_type == "mp_qrcode")
        
        # 如果是 API 登录，先执行登录逻辑，不启动浏览器
        if use_api_login:
            from .login_api import WeChatAPILogin
            utils.logger.info("[WeChatCrawler] Using API login mode (mp_qrcode)")
            
            api_login = WeChatAPILogin()
            if await api_login.run():
                token, cookies = api_login.get_results()
                
                # API 登录成功，更新 Cookie 字符串
                if cookies:
                    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                    # 将 API 获取的 Cookie 更新到 config 中，以便后续使用
                    config.COOKIES = cookie_str
                    
                # 设置 Token
                if token:
                    # 暂时保存 token，待 client 初始化后设置
                    pass
                    
                # 如果是仅登录模式，直接返回，不启动浏览器
                login_only = getattr(config, 'LOGIN_ONLY', False)
                if login_only:
                    utils.logger.info("[WeChatCrawler] API Login successful (Login Only mode)")
                    return
            else:
                utils.logger.error("[WeChatCrawler] API login failed")
                return

        # 启动浏览器 (非 API 登录模式，或 API 登录后需要继续爬取)
        async with async_playwright() as playwright:
            # 选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[WeChatCrawler] Launching browser with CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[WeChatCrawler] Launching browser with standard mode")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, 
                    playwright_proxy_format, 
                    self.user_agent, 
                    headless=config.HEADLESS
                )
                # 添加stealth脚本
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)
            await asyncio.sleep(2)

            # 创建客户端
            self.wechat_client = await self.create_wechat_client(httpx_proxy_format)
            
            # 如果之前 API 登录成功，注入 Cookie 和 Token
            if use_api_login and 'api_login' in locals():
                token, cookies = api_login.get_results()
                if cookies:
                    playwright_cookies = []
                    for k, v in cookies.items():
                        playwright_cookies.append({
                            'name': k,
                            'value': v,
                            'domain': ".weixin.qq.com",
                            'path': "/"
                        })
                    await self.browser_context.add_cookies(playwright_cookies)
                    await self.wechat_client.update_cookies(browser_context=self.browser_context)
                
                if token:
                    self.wechat_client.set_token(token)
                    utils.logger.info(f"[WeChatCrawler] Token set from API login: {token}")
            
            # 首先检查是否已经登录（从当前页面URL或cookies中提取token）
            # 注意：如果 API 登录成功，这里应该能检测到
            is_logged_in = await self._check_existing_login()
            
            if not is_logged_in and not use_api_login:
                cookie_str = self._get_account_cookies() or config.COOKIES
                
                # 浏览器自动化登录模式
                utils.logger.info(f"[WeChatCrawler] Using Browser login mode ({login_type})")
                login_obj = WeChatLogin(
                    login_type=login_type,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=cookie_str,
                )
                await login_obj.begin()
                
                # 登录后更新cookies
                await self.wechat_client.update_cookies(browser_context=self.browser_context)
                
                # 设置token
                token = login_obj.get_token()
                if token:
                    self.wechat_client.set_token(token)
            
            # 检查是否为仅登录模式
            login_only = getattr(config, 'LOGIN_ONLY', False)
            if login_only:
                utils.logger.info("[WeChatCrawler] Login only mode - skipping crawling")
                utils.logger.info("[WeChatCrawler] Cookies and Token have been captured successfully!")
                return
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            
            # 根据爬取类型执行不同的操作
            if config.CRAWLER_TYPE == "search":
                # 搜索公众号模式
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # 指定文章详情模式
                await self.get_specified_articles()
            elif config.CRAWLER_TYPE == "creator":
                # 指定公众号主页模式
                await self.get_creators_articles()
            elif config.CRAWLER_TYPE == "album":
                # 合集模式
                await self.get_album_articles()
            else:
                utils.logger.error(f"[WeChatCrawler] Invalid crawler type: {config.CRAWLER_TYPE}")

            utils.logger.info("[WeChatCrawler] WeChat crawler finished ...")

    async def search(self):
        """搜索公众号并爬取文章"""
        utils.logger.info("[WeChatCrawler.search] Begin search WeChat accounts...")
        
        # 从配置读取关键词
        keywords = config.KEYWORDS.split(",")
        
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
            
            utils.logger.info(f"[WeChatCrawler.search] Searching for: {keyword}")
            
            try:
                # 搜索公众号
                result = await self.wechat_client.search_account(keyword, begin=0, count=5)
                
                if result.get("base_resp", {}).get("ret") != 0:
                    utils.logger.error(f"[WeChatCrawler.search] Search failed: {result}")
                    continue
                
                # 获取公众号列表
                accounts = result.get("list", [])
                utils.logger.info(f"[WeChatCrawler.search] Found {len(accounts)} accounts")
                
                # 遍历公众号
                for account in accounts:
                    fakeid = account.get("fakeid")
                    nickname = account.get("nickname", "Unknown")
                    
                    if not fakeid:
                        continue
                    
                    utils.logger.info(f"[WeChatCrawler.search] Processing account: {nickname} (fakeid: {fakeid})")
                    
                    # 1. 尝试获取文章总数
                    try:
                        profile_res = await self.wechat_client.get_account_profile(fakeid)
                        app_msg_cnt = profile_res.get("app_msg_cnt")
                        if app_msg_cnt is not None:
                            account["total_article_count"] = int(app_msg_cnt)
                            utils.logger.info(f"[WeChatCrawler.search] Total articles: {app_msg_cnt}")
                            
                            # 保存公众号信息（包含总数）
                            from store import wechat as wechat_store
                            await wechat_store.store_creator(account)
                    except Exception as e:
                        utils.logger.warning(f"[WeChatCrawler.search] Failed to get profile stats: {e}")
                    
                    # 2. 爬取该公众号的文章
                    await self.get_account_articles(fakeid, nickname)
                    
                    # 延迟
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                    
            except Exception as e:
                utils.logger.error(f"[WeChatCrawler.search] Error processing keyword {keyword}: {e}")
                continue

    async def get_account_articles(self, fakeid: str, nickname: str = ""):
        """获取指定公众号的文章（支持增量爬取）"""
        utils.logger.info(f"[WeChatCrawler.get_account_articles] Getting articles for: {nickname} ({fakeid})")
        
        # 尝试更新一次总数（针对 creator 模式单独调用的情况）
        try:
            profile_res = await self.wechat_client.get_account_profile(fakeid)
            app_msg_cnt = profile_res.get("app_msg_cnt")
            if app_msg_cnt is not None:
                account_info = {
                    "fakeid": fakeid,
                    "nickname": nickname,
                    "total_article_count": int(app_msg_cnt)
                }
                from store import wechat as wechat_store
                await wechat_store.store_creator(account_info)
                utils.logger.info(f"[WeChatCrawler.get_account_articles] Updated total count: {app_msg_cnt}")
        except Exception as e:
            utils.logger.warning(f"[WeChatCrawler.get_account_articles] Failed to update total count: {e}")
        
        # 检查是否启用增量爬取
        # 优先使用全局配置（由命令行参数设置），其次使用微信专用配置
        enable_incremental = getattr(config, "ENABLE_INCREMENTAL_CRAWL", False) or \
                            getattr(wechat_config, "ENABLE_WECHAT_INCREMENTAL", False)
        incremental_handler = None
        
        utils.logger.info(
            f"[WeChatCrawler.get_account_articles] 增量爬取配置: "
            f"ENABLE_INCREMENTAL_CRAWL={getattr(config, 'ENABLE_INCREMENTAL_CRAWL', False)}, "
            f"ENABLE_WECHAT_INCREMENTAL={getattr(wechat_config, 'ENABLE_WECHAT_INCREMENTAL', False)}, "
            f"最终启用={enable_incremental}"
        )
        
        if enable_incremental:
            try:
                from crawler.incremental import CreatorIncrementalHandler
                incremental_handler = CreatorIncrementalHandler(platform="wechat")
                utils.logger.info(f"[WeChatCrawler.get_account_articles] ✅ 增量爬取已启用")
            except Exception as e:
                utils.logger.warning(f"[WeChatCrawler.get_account_articles] ❌ 增量模块加载失败: {e}")
        else:
            utils.logger.info(f"[WeChatCrawler.get_account_articles] 📦 全量爬取模式")
        
        try:
            # 获取文章列表
            begin = 0
            count = 10
            # 使用微信专用配置，默认不限制（获取全部文章）
            max_articles = getattr(wechat_config, "MAX_ARTICLES_PER_ACCOUNT", 0) or float('inf')
            total_fetched = 0   # 从API获取的文章总数（遍历过的文章）
            total_inserted = 0  # 新增的文章数（数据库INSERT）
            total_updated = 0   # 更新的文章数（数据库UPDATE）
            total_skipped = 0   # 跳过的已存在文章数（增量模式下）
            total_failed = 0    # 保存失败的文章数
            # 兼容旧的 total_new 变量（表示成功保存的总数 = inserted + updated）
            total_new = 0
            
            # 增量爬取：早停计数器（优先使用微信专用配置）
            early_stop_count = 0
            early_stop_threshold = getattr(wechat_config, "WECHAT_EARLY_STOP_THRESHOLD", 0) or \
                                  getattr(config, "CREATOR_EARLY_STOP_THRESHOLD", 5)
            
            utils.logger.info(
                f"[WeChatCrawler.get_account_articles] 开始爬取: 公众号={nickname}, "
                f"max_articles={max_articles}, early_stop_threshold={early_stop_threshold}"
            )
            
            while total_new < max_articles:
                result = await self.wechat_client.get_article_list(
                    fakeid=fakeid,
                    begin=begin,
                    count=count
                )
                
                if result.get("base_resp", {}).get("ret") != 0:
                    utils.logger.error(f"[WeChatCrawler.get_account_articles] Failed to get articles: {result}")
                    break
                
                articles = result.get("articles", [])
                if not articles:
                    utils.logger.info(f"[WeChatCrawler.get_account_articles] No more articles")
                    break
                
                utils.logger.info(
                    f"[WeChatCrawler.get_account_articles] 获取第 {begin // count + 1} 页, "
                    f"本页 {len(articles)} 篇文章 (累计遍历: {total_fetched})"
                )
                
                # 保存文章（带增量检查）
                should_stop = False
                page_inserted = 0
                page_updated = 0
                page_skipped = 0
                page_failed = 0
                
                for article in articles:
                    article_id = article.get("aid", "")
                    article_title = article.get("title", "")[:30]
                    total_fetched += 1  # 遍历计数
                    
                    # 增量爬取：检查文章是否已存在
                    if incremental_handler:
                        is_exists = await incremental_handler.should_stop_crawling(article_id, fakeid)
                        if is_exists:
                            early_stop_count += 1
                            total_skipped += 1
                            page_skipped += 1
                            utils.logger.debug(
                                f"[WeChatCrawler] 文章已存在: {article_id} ({article_title}...), "
                                f"连续计数: {early_stop_count}/{early_stop_threshold}"
                            )
                            
                            # 连续 N 条已存在，触发早停
                            if early_stop_count >= early_stop_threshold:
                                utils.logger.info(
                                    f"[WeChatCrawler] 🛑 触发早停: 连续 {early_stop_threshold} 条文章已存在, "
                                    f"公众号: {nickname}, 遍历: {total_fetched}, 新增: {total_new}, 跳过: {total_skipped}"
                                )
                                should_stop = True
                                break
                            continue  # 跳过已存在的文章，不保存
                        else:
                            # 发现新文章，重置计数
                            early_stop_count = 0
                    
                    # 保存文章
                    utils.logger.info(
                        f"[WeChatCrawler.get_account_articles] 准备保存文章 #{total_fetched}: "
                        f"id={article_id}, title={article_title}"
                    )
                    save_result = await self.save_article(article, fakeid, nickname)
                    
                    if save_result == "inserted":
                        total_inserted += 1
                        page_inserted += 1
                        total_new += 1
                        utils.logger.info(
                            f"[WeChatCrawler.get_account_articles] ✅ 新增成功 (总新增={total_inserted}): "
                            f"id={article_id}, title={article_title}"
                        )
                    elif save_result == "updated":
                        total_updated += 1
                        page_updated += 1
                        total_new += 1
                        utils.logger.info(
                            f"[WeChatCrawler.get_account_articles] ✅ 更新成功 (总更新={total_updated}): "
                            f"id={article_id}, title={article_title}"
                        )
                    else:
                        total_failed += 1
                        page_failed += 1
                        utils.logger.warning(
                            f"[WeChatCrawler.get_account_articles] ❌ 保存失败: "
                            f"id={article_id}, title={article_title}, result={save_result}"
                        )
                    
                    if total_new >= max_articles:
                        utils.logger.info(
                            f"[WeChatCrawler.get_account_articles] 达到最大文章数限制: {max_articles}"
                        )
                        break
                
                # 本页统计
                utils.logger.info(
                    f"[WeChatCrawler.get_account_articles] 第 {begin // count + 1} 页完成: "
                    f"新增={page_inserted}, 更新={page_updated}, 跳过={page_skipped}, 失败={page_failed} | "
                    f"累计: 遍历={total_fetched}, 新增={total_inserted}, 更新={total_updated}, 跳过={total_skipped}, 失败={total_failed}"
                )
                
                if should_stop:
                    break
                
                # 下一页
                begin += count
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            
            # 输出最终统计
            utils.logger.info(
                f"[WeChatCrawler.get_account_articles] ✅ 完成: 公众号={nickname}, "
                f"遍历={total_fetched}, 新增={total_inserted}, 更新={total_updated}, 跳过={total_skipped}, 失败={total_failed}"
            )
            
            # 如果有失败的文章，记录警告
            if total_failed > 0:
                utils.logger.warning(
                    f"[WeChatCrawler.get_account_articles] ⚠️ 有 {total_failed} 篇文章保存失败, "
                    f"请检查数据库连接和存储配置"
                )
                
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler.get_account_articles] Error: {e}")

    async def save_article(self, article: Dict, fakeid: str = "", account_name: str = "") -> bool:
        """
        保存文章数据
        
        Returns:
            bool: 保存成功返回 True，失败返回 False
        """
        article_id = article.get("aid", "")
        article_title = article.get("title", "")
        
        try:
            article_link = article.get("link", "")
            
            # 提取文章信息
            article_data = {
                "article_id": article_id,
                "title": article_title,
                "link": article_link,
                "cover": article.get("cover", ""),
                "digest": article.get("digest", ""),
                "create_time": article.get("create_time", 0),
                "update_time": article.get("update_time", 0),
                "author": article.get("author", ""),
                "fakeid": fakeid,
                "account_name": account_name,
                "content": "",  # HTML内容
                "read_num": 0,
                "like_num": 0,
                "old_like_num": 0,
                "share_num": 0,
                "comment_count": 0,
            }
            
            utils.logger.info(f"[WeChatCrawler.save_article] 开始保存文章: id={article_id}, title={article_title[:30]}")
            
            # 如果启用了文章内容下载，获取HTML内容
            if wechat_config.ENABLE_GET_ARTICLE_CONTENT and article_link:
                try:
                    utils.logger.info(f"[WeChatCrawler.save_article] Downloading HTML content...")
                    
                    # 判断是否需要使用凭证（用于获取阅读量）
                    with_credential = wechat_config.ENABLE_GET_READING_STATS
                    
                    html_content = await self.wechat_client.get_article_html(
                        article_link,
                        with_credential=with_credential
                    )
                    
                    if html_content:
                        # 如果启用了资源下载，下载文章中的图片、视频等资源
                        if getattr(config, "ENABLE_DOWNLOAD_RESOURCES", False):
                            try:
                                from .resource_downloader import WeChatResourceDownloader
                                
                                utils.logger.info(f"[WeChatCrawler.save_article] Downloading resources...")
                                downloader = WeChatResourceDownloader()
                                
                                # 下载资源并获取处理后的HTML
                                processed_html, resource_stats = await downloader.download_article_resources(
                                    html_content,
                                    article_data["article_id"],
                                    timeout=60
                                )
                                
                                article_data["content"] = processed_html
                                utils.logger.info(
                                    f"[WeChatCrawler.save_article] Resources downloaded: "
                                    f"images={resource_stats['images']}, "
                                    f"videos={resource_stats['videos']}, "
                                    f"audios={resource_stats['audios']}"
                                )
                            except Exception as e:
                                utils.logger.error(f"[WeChatCrawler.save_article] Error downloading resources: {e}")
                                article_data["content"] = html_content
                        else:
                            article_data["content"] = html_content
                        
                        utils.logger.info(f"[WeChatCrawler.save_article] HTML content downloaded successfully")
                        
                        # 如果启用了阅读量统计，从HTML中提取阅读量数据
                        if with_credential:
                            stats = self._extract_reading_stats_from_html(html_content)
                            if stats:
                                article_data["read_num"] = stats.get("read_num", 0)
                                article_data["like_num"] = stats.get("like_num", 0)
                                article_data["old_like_num"] = stats.get("old_like_num", 0)
                                article_data["share_num"] = stats.get("share_num", 0)
                                article_data["comment_count"] = stats.get("comment_num", 0)
                                utils.logger.info(
                                    f"[WeChatCrawler.save_article] Stats extracted: "
                                    f"read={article_data['read_num']}, like={article_data['like_num']}, "
                                    f"share={article_data['share_num']}, comment={article_data['comment_count']}"
                                )
                    else:
                        utils.logger.warning(f"[WeChatCrawler.save_article] Failed to download HTML content, url: {article_link}")
                    
                    # 添加延迟，避免请求过快
                    if wechat_config.ARTICLE_CONTENT_CRAWL_DELAY > 0:
                        await asyncio.sleep(wechat_config.ARTICLE_CONTENT_CRAWL_DELAY)
                        
                except Exception as e:
                    utils.logger.error(f"[WeChatCrawler.save_article] Error downloading HTML: {e}")
            
            # 调用存储层保存数据
            from store import wechat as wechat_store
            utils.logger.debug(f"[WeChatCrawler.save_article] 调用存储层保存: id={article_id}")
            store_result = await wechat_store.update_wechat_article(article_data)
            utils.logger.info(f"[WeChatCrawler.save_article] ✅ 存储层保存完成: id={article_id}, result={store_result}")
            
            # 如果启用了评论爬取，获取评论
            comments = []
            if config.ENABLE_GET_COMMENTS:
                comments = await self.get_article_comments(article_data)
            
            # 如果启用了导出功能，执行导出
            if getattr(config, "ENABLE_EXPORT", False) and article_data.get("content"):
                await self._export_article(article_data, comments)
            
            utils.logger.info(f"[WeChatCrawler.save_article] ✅ 文章保存成功: id={article_id}, title={article_title[:30]}")
            # 返回存储结果: "inserted", "updated", 或 "error"
            return store_result if store_result else "error"
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler.save_article] ❌ 保存文章失败: id={article_id}, title={article_title[:30]}, error={e}")
            import traceback
            utils.logger.error(f"[WeChatCrawler.save_article] 堆栈信息: {traceback.format_exc()}")
            return False
    
    async def _export_article(self, article_data: Dict, comments: Optional[List[Dict]] = None):
        """
        导出文章到指定格式
        
        Args:
            article_data: 文章数据
            comments: 评论列表
        """
        try:
            from .exporter import WeChatArticleExporter
            
            export_format = getattr(config, "EXPORT_FORMAT", "html")
            export_path = getattr(config, "EXPORT_PATH", "data/wechat_exports")
            include_comments = getattr(config, "EXPORT_HTML_INCLUDE_COMMENTS", True)
            include_images = getattr(config, "EXPORT_INCLUDE_IMAGES", True)
            
            html_content = article_data.get("content", "")
            if not html_content:
                utils.logger.warning("[WeChatCrawler._export_article] No HTML content to export")
                return
            
            exporter = WeChatArticleExporter(base_export_path=export_path)
            
            # 支持多种格式
            formats = [export_format] if isinstance(export_format, str) else export_format
            
            for fmt in formats:
                fmt = fmt.lower().strip()
                
                try:
                    if fmt == "html":
                        export_dir, stats = await exporter.export_article_html(
                            html_content,
                            article_data,
                            include_comments=include_comments,
                            comments=comments
                        )
                        utils.logger.info(f"[WeChatCrawler._export_article] HTML exported to: {export_dir}")
                    
                    elif fmt == "markdown" or fmt == "md":
                        export_path = await exporter.export_article_markdown(
                            html_content,
                            article_data,
                            include_images=include_images
                        )
                        utils.logger.info(f"[WeChatCrawler._export_article] Markdown exported to: {export_path}")
                    
                    elif fmt == "txt" or fmt == "text":
                        export_path = await exporter.export_article_txt(
                            html_content,
                            article_data
                        )
                        utils.logger.info(f"[WeChatCrawler._export_article] TXT exported to: {export_path}")
                    
                    elif fmt == "docx" or fmt == "word":
                        export_path = await exporter.export_article_docx(
                            html_content,
                            article_data,
                            include_images=include_images
                        )
                        if export_path:
                            utils.logger.info(f"[WeChatCrawler._export_article] DOCX exported to: {export_path}")
                        else:
                            utils.logger.warning("[WeChatCrawler._export_article] DOCX export failed (python-docx not installed?)")
                    
                    else:
                        utils.logger.warning(f"[WeChatCrawler._export_article] Unknown export format: {fmt}")
                
                except Exception as e:
                    utils.logger.error(f"[WeChatCrawler._export_article] Error exporting to {fmt}: {e}")
                    
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._export_article] Export error: {e}")

    def _extract_reading_stats_from_html(self, html: str) -> Optional[Dict]:
        """
        从HTML中提取阅读量和点赞数等统计数据
        
        采用多种提取策略：
        1. 优先从 window.cgiDataNew 中提取精确数据（参考 wechat-article-exporter）
        2. 回退到正则表达式提取
        
        Args:
            html: 文章HTML内容
            
        Returns:
            包含阅读量数据的字典，如果提取失败返回None
        """
        import re
        import json
        
        try:
            result = {
                "read_num": 0,
                "like_num": 0,
                "old_like_num": 0,
                "share_num": 0,
                "comment_num": 0,
            }
            
            # 策略1: 从 window.cgiDataNew 提取（最精确的方式）
            cgi_data = self._extract_cgi_data_new(html)
            if cgi_data:
                try:
                    # 从 user_info.appmsg_bar_data 获取统计数据
                    user_info = cgi_data.get("user_info", {})
                    appmsg_bar_data = user_info.get("appmsg_bar_data", {})
                    
                    if appmsg_bar_data:
                        result["read_num"] = appmsg_bar_data.get("read_num", 0) or 0
                        result["old_like_num"] = appmsg_bar_data.get("old_like_count", 0) or 0
                        result["share_num"] = appmsg_bar_data.get("share_count", 0) or 0
                        result["like_num"] = appmsg_bar_data.get("like_count", 0) or 0
                        result["comment_num"] = appmsg_bar_data.get("comment_count", 0) or 0
                        
                        utils.logger.info(
                            f"[WeChatCrawler._extract_reading_stats_from_html] "
                            f"Extracted from cgiDataNew: read={result['read_num']}, "
                            f"like={result['like_num']}, share={result['share_num']}"
                        )
                        return result
                except Exception as e:
                    utils.logger.warning(f"[WeChatCrawler._extract_reading_stats_from_html] cgiDataNew parse error: {e}")
            
            # 策略2: 从 appmsgstat 变量提取
            appmsgstat_match = re.search(
                r'var\s+appmsgstat\s*=\s*(\{[^}]+\})',
                html, re.DOTALL
            )
            if appmsgstat_match:
                try:
                    # 清理JS对象字符串，转为JSON
                    stat_str = appmsgstat_match.group(1)
                    stat_str = re.sub(r'(\w+):', r'"\1":', stat_str)
                    stat_str = stat_str.replace("'", '"')
                    stat_data = json.loads(stat_str)
                    
                    result["read_num"] = stat_data.get("read_num", 0) or 0
                    result["like_num"] = stat_data.get("like_num", 0) or 0
                    result["old_like_num"] = stat_data.get("old_like_num", 0) or 0
                    
                    if result["read_num"] > 0:
                        utils.logger.info(
                            f"[WeChatCrawler._extract_reading_stats_from_html] "
                            f"Extracted from appmsgstat: read={result['read_num']}"
                        )
                        return result
                except Exception as e:
                    utils.logger.warning(f"[WeChatCrawler._extract_reading_stats_from_html] appmsgstat parse error: {e}")
            
            # 策略3: 正则表达式提取（回退方案）
            # 阅读量
            read_match = re.search(r'var\s+read_num\s*=\s*["\']?(\d+)["\']?', html)
            if not read_match:
                read_match = re.search(r'"read_num"\s*:\s*["\']?(\d+)["\']?', html)
            if not read_match:
                read_match = re.search(r'read_num\s*:\s*["\']?(\d+)["\']?', html)
            
            # 点赞数（在看）
            like_match = re.search(r'var\s+like_num\s*=\s*["\']?(\d+)["\']?', html)
            if not like_match:
                like_match = re.search(r'"like_num"\s*:\s*["\']?(\d+)["\']?', html)
            if not like_match:
                like_match = re.search(r'like_num\s*:\s*["\']?(\d+)["\']?', html)
            
            # 旧版点赞数
            old_like_match = re.search(r'"old_like_count"\s*:\s*["\']?(\d+)["\']?', html)
            if not old_like_match:
                old_like_match = re.search(r'old_like_num\s*:\s*["\']?(\d+)["\']?', html)
            
            # 分享数
            share_match = re.search(r'"share_count"\s*:\s*["\']?(\d+)["\']?', html)
            
            # 评论数
            comment_match = re.search(r'"comment_count"\s*:\s*["\']?(\d+)["\']?', html)
            
            if read_match:
                result["read_num"] = int(read_match.group(1))
            if like_match:
                result["like_num"] = int(like_match.group(1))
            if old_like_match:
                result["old_like_num"] = int(old_like_match.group(1))
            if share_match:
                result["share_num"] = int(share_match.group(1))
            if comment_match:
                result["comment_num"] = int(comment_match.group(1))
            
            # 处理带单位的数字字符串（如 "10w+"）
            read_str_match = re.search(r'var\s+read_num\s*=\s*["\']([^"\']+)["\']', html)
            if read_str_match and result["read_num"] == 0:
                result["read_num"] = self._parse_count_string(read_str_match.group(1))
            
            if result["read_num"] > 0 or result["like_num"] > 0:
                utils.logger.info(
                    f"[WeChatCrawler._extract_reading_stats_from_html] "
                    f"Extracted via regex: read={result['read_num']}, like={result['like_num']}"
                )
                return result
            
            return None
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._extract_reading_stats_from_html] Error: {e}")
            return None
    
    def _extract_cgi_data_new(self, html: str) -> Optional[Dict]:
        """
        从HTML中提取 window.cgiDataNew 对象
        
        这是微信文章页面中包含阅读量等统计数据的主要数据源。
        参考 wechat-article-exporter 的实现方式。
        
        Args:
            html: 文章HTML内容
            
        Returns:
            解析后的cgiDataNew对象，如果提取失败返回None
        """
        import re
        import json
        
        try:
            # 查找包含 window.cgiDataNew 的 script 标签
            # 格式通常是: window.cgiDataNew = {...}
            pattern = r'window\.cgiDataNew\s*=\s*(\{[\s\S]*?\});?\s*(?:window\.|</script>|$)'
            match = re.search(pattern, html)
            
            if not match:
                # 尝试其他模式
                pattern2 = r'var\s+cgiDataNew\s*=\s*(\{[\s\S]*?\});'
                match = re.search(pattern2, html)
            
            if not match:
                return None
            
            js_obj_str = match.group(1)
            
            # 清理并转换JS对象为JSON
            cgi_data = self._js_object_to_json(js_obj_str)
            
            if cgi_data:
                utils.logger.debug("[WeChatCrawler._extract_cgi_data_new] Successfully extracted cgiDataNew")
                return cgi_data
            
            return None
            
        except Exception as e:
            utils.logger.warning(f"[WeChatCrawler._extract_cgi_data_new] Error: {e}")
            return None
    
    def _js_object_to_json(self, js_str: str) -> Optional[Dict]:
        """
        将JavaScript对象字符串转换为Python字典
        
        处理JS对象特有的语法，如：
        - 无引号的键名
        - 单引号字符串
        - 尾随逗号
        - undefined/null值
        
        Args:
            js_str: JavaScript对象字符串
            
        Returns:
            解析后的字典，如果解析失败返回None
        """
        import re
        import json
        
        try:
            # 移除注释
            js_str = re.sub(r'//[^\n]*', '', js_str)
            js_str = re.sub(r'/\*[\s\S]*?\*/', '', js_str)
            
            # 处理无引号的键名: key: -> "key":
            # 但要避免处理URL中的冒号
            js_str = re.sub(r'(?<=[{,\s])(\w+)\s*:', r'"\1":', js_str)
            
            # 单引号转双引号（但要小心处理转义）
            js_str = js_str.replace("'", '"')
            
            # 处理特殊值
            js_str = re.sub(r'\bundefined\b', 'null', js_str)
            js_str = re.sub(r'\bNaN\b', '0', js_str)
            js_str = re.sub(r'\bInfinity\b', '999999999', js_str)
            
            # 移除尾随逗号
            js_str = re.sub(r',\s*([}\]])', r'\1', js_str)
            
            # 尝试解析
            return json.loads(js_str)
            
        except json.JSONDecodeError:
            # 如果标准解析失败，尝试更激进的清理
            try:
                # 只提取我们需要的数据部分
                # 查找 appmsg_bar_data 部分
                bar_data_match = re.search(
                    r'"?appmsg_bar_data"?\s*:\s*(\{[^}]+\})',
                    js_str, re.DOTALL
                )
                
                if bar_data_match:
                    bar_str = bar_data_match.group(1)
                    # 清理并解析
                    bar_str = re.sub(r'(\w+)\s*:', r'"\1":', bar_str)
                    bar_str = bar_str.replace("'", '"')
                    bar_str = re.sub(r',\s*}', '}', bar_str)
                    
                    bar_data = json.loads(bar_str)
                    return {"user_info": {"appmsg_bar_data": bar_data}}
                
                return None
                
            except Exception:
                return None
        except Exception:
            return None
    
    def _extract_article_info_from_html(self, html: str) -> Optional[Dict]:
        """
        从HTML中提取文章基本信息
        
        Args:
            html: 文章HTML内容
            
        Returns:
            包含文章信息的字典
        """
        from bs4 import BeautifulSoup
        import re
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            info = {}
            
            # 提取标题
            title_elem = soup.find('h1', class_='rich_media_title') or soup.find('h2', id='activity-name')
            if title_elem:
                info['title'] = title_elem.get_text(strip=True)
            
            # 提取作者
            author_elem = soup.find('a', id='js_name') or soup.find('span', class_='rich_media_meta rich_media_meta_nickname')
            if author_elem:
                info['author'] = author_elem.get_text(strip=True)
            elif soup.find('div', id='meta_content'):
                meta = soup.find('div', id='meta_content')
                author_text = meta.find('span', class_='rich_media_meta_text')
                if author_text:
                    info['author'] = author_text.get_text(strip=True)
            
            # 提取公众号名称
            account_elem = soup.find('strong', class_='profile_nickname')
            if account_elem:
                info['account_name'] = account_elem.get_text(strip=True)
            
            # 提取发布时间
            time_elem = soup.find('em', id='publish_time') or soup.find('span', class_='rich_media_meta rich_media_meta_text')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 尝试解析时间字符串
                import time
                try:
                    # 可能的格式：2024-01-27, 2024-01-27 10:30 等
                    for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y年%m月%d日']:
                        try:
                            dt = time.strptime(time_text, fmt)
                            info['create_time'] = int(time.mktime(dt))
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            # 提取摘要（如果有）
            desc_elem = soup.find('meta', {'name': 'description'})
            if desc_elem and desc_elem.get('content'):
                info['digest'] = desc_elem.get('content')
            
            # 提取封面图
            cover_elem = soup.find('meta', {'property': 'og:image'})
            if cover_elem and cover_elem.get('content'):
                info['cover'] = cover_elem.get('content')
            
            return info if info else None
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._extract_article_info_from_html] Error: {e}")
            return None
    
    def _parse_count_string(self, count_str: str) -> int:
        """
        解析计数字符串，如 "10w+", "1000+", "100" 等
        
        Args:
            count_str: 计数字符串
            
        Returns:
            整数值
        """
        try:
            count_str = count_str.strip()
            
            # 处理 "10w+" 格式（万）
            if 'w' in count_str.lower():
                num_str = count_str.lower().replace('w', '').replace('+', '').strip()
                return int(float(num_str) * 10000)
            
            # 处理 "1000+" 格式
            if '+' in count_str:
                num_str = count_str.replace('+', '').strip()
                return int(num_str)
            
            # 直接转换数字
            return int(count_str)
            
        except Exception:
            return 0

    async def get_article_comments(self, article: Dict) -> List[Dict]:
        """获取文章评论（支持分页获取所有评论和回复）
        
        Returns:
            评论列表（用于导出等功能）
        """
        try:
            # 检查是否有必要的凭证
            credentials = getattr(config, "WECHAT_CREDENTIALS", {})
            if not credentials.get("uin") or not credentials.get("key"):
                utils.logger.warning("[WeChatCrawler.get_article_comments] Missing credentials, skip comments")
                return []
            
            article_id = article.get("article_id", "")
            link = article.get("link", "")
            
            if not link:
                return []
            
            # 从链接中提取__biz参数
            from .help import extract_article_url_params
            params = extract_article_url_params(link)
            
            if not params or not params.get("__biz"):
                utils.logger.warning(f"[WeChatCrawler.get_article_comments] Cannot extract biz from link: {link}")
                return []
            
            biz = params["__biz"]
            
            # 如果文章内容中包含comment_id，直接使用
            comment_id = None
            if article.get("content"):
                comment_id = self.wechat_client._extract_comment_id(article["content"])
            
            if not comment_id:
                utils.logger.warning(f"[WeChatCrawler.get_article_comments] No comment_id found for: {article_id}")
                return []
            
            # 分页获取所有评论
            utils.logger.info(f"[WeChatCrawler.get_article_comments] Getting comments for article: {article_id}")
            
            all_comments = []
            buffer = ""
            continue_flag = True
            page = 0
            
            # 获取顶级评论（分页）
            while continue_flag:
                try:
                    page += 1
                    utils.logger.info(f"[WeChatCrawler.get_article_comments] Fetching page {page}")
                    
                    comments_data = await self.wechat_client.get_comments(
                        biz=biz,
                        comment_id=comment_id,
                        uin=credentials["uin"],
                        key=credentials["key"],
                        pass_ticket=credentials.get("pass_ticket", ""),
                        buffer=buffer,
                        offset=1,
                        limit=100
                    )
                    
                    if comments_data.get("base_resp", {}).get("ret") == 0:
                        # 成功获取评论
                        elected = comments_data.get("elected_comment", [])
                        normal = comments_data.get("comment", [])
                        all_comments.extend(elected + normal)
                        
                        # 检查是否还有更多
                        buffer = comments_data.get("buffer", "")
                        continue_flag = comments_data.get("continue_flag", 0) == 1
                        
                        utils.logger.info(
                            f"[WeChatCrawler.get_article_comments] Page {page}: "
                            f"elected={len(elected)}, normal={len(normal)}, "
                            f"continue={continue_flag}"
                        )
                    else:
                        utils.logger.error(
                            f"[WeChatCrawler.get_article_comments] Failed to get comments: "
                            f"{comments_data.get('base_resp', {})}"
                        )
                        break
                    
                    # 添加延迟，避免请求过快
                    if continue_flag:
                        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                        
                except Exception as e:
                    utils.logger.error(f"[WeChatCrawler.get_article_comments] Error on page {page}: {e}")
                    break
            
            utils.logger.info(f"[WeChatCrawler.get_article_comments] Total comments: {len(all_comments)}")
            
            # 获取需要获取回复的评论
            comments_need_replies = []
            for comment in all_comments:
                reply_info = comment.get("reply_new", {}) or comment.get("reply", {})
                total_replies = reply_info.get("reply_total_cnt", 0)
                current_replies = len(reply_info.get("reply_list", []))
                
                if total_replies > current_replies:
                    comments_need_replies.append(comment)
            
            utils.logger.info(
                f"[WeChatCrawler.get_article_comments] "
                f"{len(comments_need_replies)} comments need more replies"
            )
            
            # 获取评论回复
            for comment in comments_need_replies:
                try:
                    content_id = comment.get("content_id", "")
                    reply_info = comment.get("reply_new", {}) or comment.get("reply", {})
                    max_reply_id = reply_info.get("max_reply_id", 0)
                    
                    if not content_id:
                        continue
                    
                    utils.logger.info(
                        f"[WeChatCrawler.get_article_comments] "
                        f"Fetching more replies for comment {content_id}"
                    )
                    
                    reply_data = await self.wechat_client.get_comment_replies(
                        biz=biz,
                        comment_id=comment_id,
                        content_id=content_id,
                        uin=credentials["uin"],
                        key=credentials["key"],
                        pass_ticket=credentials.get("pass_ticket", ""),
                        max_reply_id=max_reply_id,
                        limit=100
                    )
                    
                    if reply_data.get("base_resp", {}).get("ret") == 0:
                        # 将新获取的回复添加到评论中
                        new_replies = reply_data.get("reply_list", [])
                        if new_replies:
                            if "reply_new" in comment:
                                comment["reply_new"]["reply_list"].extend(new_replies)
                            elif "reply" in comment:
                                comment["reply"]["reply_list"].extend(new_replies)
                            
                            utils.logger.info(
                                f"[WeChatCrawler.get_article_comments] "
                                f"Added {len(new_replies)} replies to comment {content_id}"
                            )
                    
                    # 添加延迟
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                    
                except Exception as e:
                    utils.logger.error(
                        f"[WeChatCrawler.get_article_comments] "
                        f"Error getting replies for comment {content_id}: {e}"
                    )
            
            # 保存所有评论数据
            if all_comments:
                await self._save_comments_list(all_comments, article_id)
            
            # 返回格式化后的评论列表（用于导出）
            return self._format_comments_for_export(all_comments)
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler.get_article_comments] Error getting comments: {e}")
            return []
    
    def _format_comments_for_export(self, comments: List[Dict]) -> List[Dict]:
        """
        格式化评论列表用于导出
        
        Args:
            comments: 原始评论列表
            
        Returns:
            格式化后的评论列表
        """
        formatted = []
        for comment in comments:
            item = {
                "comment_id": str(comment.get("id", "") or comment.get("content_id", "")),
                "content": comment.get("content", ""),
                "create_time": comment.get("create_time", 0),
                "like_num": comment.get("like_num", 0),
                "nick_name": comment.get("nick_name", ""),
                "logo_url": comment.get("logo_url", ""),
                "reply_list": [],
            }
            
            # 处理回复列表
            reply_info = comment.get("reply_new", {}) or comment.get("reply", {})
            reply_list = reply_info.get("reply_list", [])
            
            for reply in reply_list:
                reply_item = {
                    "reply_id": str(reply.get("reply_id", "")),
                    "content": reply.get("content", ""),
                    "create_time": reply.get("create_time", 0),
                    "like_num": reply.get("reply_like_num", 0),
                    "nick_name": reply.get("nick_name", ""),
                }
                item["reply_list"].append(reply_item)
            
            formatted.append(item)
        
        return formatted

    async def _save_comments_list(self, comments: List[Dict], article_id: str):
        """
        保存评论列表
        
        Args:
            comments: 评论列表
            article_id: 文章ID
        """
        try:
            from store import wechat as wechat_store
            
            utils.logger.info(f"[WeChatCrawler._save_comments_list] Saving {len(comments)} comments")
            
            for comment in comments:
                comment_item = {
                    "comment_id": str(comment.get("id", "") or comment.get("content_id", "")),
                    "content": comment.get("content", ""),
                    "create_time": comment.get("create_time", 0),
                    "like_num": comment.get("like_num", 0),
                    "nick_name": comment.get("nick_name", ""),
                    "logo_url": comment.get("logo_url", ""),
                    "reply_list": [],
                }
                
                # 处理回复列表（可能在reply_new或reply中）
                reply_info = comment.get("reply_new", {}) or comment.get("reply", {})
                reply_list = reply_info.get("reply_list", [])
                
                for reply in reply_list:
                    reply_item = {
                        "reply_id": str(reply.get("reply_id", "")),
                        "content": reply.get("content", ""),
                        "create_time": reply.get("create_time", 0),
                        "like_num": reply.get("reply_like_num", 0),
                        "nick_name": reply.get("nick_name", ""),
                    }
                    comment_item["reply_list"].append(reply_item)
                
                # 保存评论（注意：store层的方法需要article_id作为单独参数）
                await wechat_store.update_wechat_comment(article_id, comment_item)
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._save_comments_list] Error saving comments: {e}")

    async def get_specified_articles(self):
        """获取指定文章列表"""
        utils.logger.info("[WeChatCrawler.get_specified_articles] Getting specified articles...")
        
        # 从配置读取文章URL列表
        article_urls = getattr(config, "WECHAT_ARTICLE_URLS", [])
        
        if not article_urls:
            utils.logger.warning("[WeChatCrawler.get_specified_articles] No article URLs configured")
            return
        
        utils.logger.info(f"[WeChatCrawler.get_specified_articles] Processing {len(article_urls)} articles")
        
        for url in article_urls:
            url = url.strip()
            if not url:
                continue
            
            try:
                utils.logger.info(f"[WeChatCrawler.get_specified_articles] Processing: {url}")
                
                # 从URL中提取文章参数
                from .help import extract_article_url_params
                params = extract_article_url_params(url)
                
                if not params:
                    utils.logger.error(f"[WeChatCrawler.get_specified_articles] Invalid URL: {url}")
                    continue
                
                # 构建文章基本信息
                article_data = {
                    "article_id": params.get("mid", ""),
                    "title": "",  # 从HTML中提取
                    "link": url,
                    "cover": "",
                    "digest": "",
                    "create_time": 0,
                    "update_time": 0,
                    "author": "",
                    "fakeid": params.get("__biz", ""),
                    "account_name": "",
                    "content": "",
                    "read_num": 0,
                    "like_num": 0,
                    "comment_count": 0,
                }
                
                # 下载文章HTML内容
                with_credential = config.ENABLE_GET_READING_STATS
                html_content = await self.wechat_client.get_article_html(
                    url,
                    with_credential=with_credential
                )
                
                if html_content:
                    article_data["content"] = html_content
                    
                    # 从HTML中提取标题和其他信息
                    article_info = self._extract_article_info_from_html(html_content)
                    if article_info:
                        article_data.update(article_info)
                    
                    # 提取阅读量数据
                    if with_credential:
                        stats = self._extract_reading_stats_from_html(html_content)
                        if stats:
                            article_data["read_num"] = stats.get("read_num", 0)
                            article_data["like_num"] = stats.get("like_num", 0)
                    
                    utils.logger.info(f"[WeChatCrawler.get_specified_articles] Article downloaded: {article_data['title'][:50]}")
                else:
                    utils.logger.warning(f"[WeChatCrawler.get_specified_articles] Failed to download: {url}")
                    continue
                
                # 保存文章数据
                from store import wechat as wechat_store
                await wechat_store.update_wechat_article(article_data)
                
                # 如果启用了评论爬取，获取评论
                if config.ENABLE_GET_COMMENTS:
                    await self.get_article_comments(article_data)
                
                # 添加延迟
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                
            except Exception as e:
                utils.logger.error(f"[WeChatCrawler.get_specified_articles] Error processing {url}: {e}")
                continue

    async def get_creators_articles(self):
        """获取指定创作者的文章"""
        utils.logger.info("[WeChatCrawler.get_creators_articles] Getting creators articles...")
        
        # 从配置读取公众号ID列表
        account_ids = getattr(wechat_config, "WECHAT_ACCOUNT_IDS", [])
        
        if not account_ids:
            utils.logger.warning("[WeChatCrawler.get_creators_articles] No account IDs configured")
            return
        
        # 从数据库获取公众号名称映射
        nickname_map = {}
        try:
            from database.db_session import get_session
            from database.models import WeChatAccount
            from sqlalchemy import select
            
            async with get_session() as session:
                stmt = select(WeChatAccount).where(WeChatAccount.fakeid.in_(account_ids))
                result = await session.execute(stmt)
                accounts = result.scalars().all()
                nickname_map = {acc.fakeid: acc.nickname for acc in accounts}
        except Exception as e:
            utils.logger.warning(f"[WeChatCrawler.get_creators_articles] Failed to get nicknames from DB: {e}")
        
        for fakeid in account_ids:
            fakeid = fakeid.strip()
            if not fakeid:
                continue
            
            nickname = nickname_map.get(fakeid, "")
            utils.logger.info(f"[WeChatCrawler.get_creators_articles] Processing fakeid: {fakeid}, nickname: {nickname}")
            await self.get_account_articles(fakeid, nickname)
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
    
    async def get_album_articles(self):
        """
        获取合集中的所有文章
        
        支持两种模式：
        1. 指定合集ID列表 (WECHAT_ALBUM_IDS)
        2. 获取指定公众号的所有合集 (WECHAT_ACCOUNT_IDS + ENABLE_CRAWL_ALL_ALBUMS)
        """
        utils.logger.info("[WeChatCrawler.get_album_articles] Getting album articles...")
        
        # 模式1: 指定合集ID列表
        album_configs = getattr(config, "WECHAT_ALBUM_IDS", [])
        
        if album_configs:
            for album_config in album_configs:
                if isinstance(album_config, dict):
                    biz = album_config.get("biz", "")
                    album_id = album_config.get("album_id", "")
                elif isinstance(album_config, str):
                    # 格式: "biz:album_id"
                    parts = album_config.split(":")
                    if len(parts) == 2:
                        biz, album_id = parts
                    else:
                        continue
                else:
                    continue
                
                if biz and album_id:
                    await self._crawl_single_album(biz, album_id)
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            return
        
        # 模式2: 获取指定公众号的所有合集
        account_ids = getattr(wechat_config, "WECHAT_ACCOUNT_IDS", [])
        crawl_all_albums = getattr(wechat_config, "ENABLE_CRAWL_ALL_ALBUMS", False)
        
        if not account_ids:
            utils.logger.warning("[WeChatCrawler.get_album_articles] No album or account IDs configured")
            return
        
        # 从数据库获取公众号名称映射
        nickname_map = {}
        try:
            from database.db_session import get_session
            from database.models import WeChatAccount
            from sqlalchemy import select
            
            async with get_session() as session:
                stmt = select(WeChatAccount).where(WeChatAccount.fakeid.in_(account_ids))
                result = await session.execute(stmt)
                accounts = result.scalars().all()
                nickname_map = {acc.fakeid: acc.nickname for acc in accounts}
        except Exception as e:
            utils.logger.warning(f"[WeChatCrawler.get_album_articles] Failed to get nicknames from DB: {e}")
        
        for fakeid in account_ids:
            fakeid = fakeid.strip()
            if not fakeid:
                continue
            
            nickname = nickname_map.get(fakeid, "")
            utils.logger.info(f"[WeChatCrawler.get_album_articles] Processing account: {fakeid} ({nickname})")
            
            if crawl_all_albums:
                # 获取该公众号的所有合集
                await self._crawl_account_albums(fakeid, nickname)
            else:
                utils.logger.warning(
                    f"[WeChatCrawler.get_album_articles] ENABLE_CRAWL_ALL_ALBUMS is False, "
                    f"please set WECHAT_ALBUM_IDS or enable ENABLE_CRAWL_ALL_ALBUMS"
                )
            
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
    
    async def _crawl_account_albums(self, fakeid: str, account_name: str = ""):
        """
        爬取指定公众号的所有合集
        
        Args:
            fakeid: 公众号fakeid
            account_name: 公众号名称（可选）
        """
        utils.logger.info(f"[WeChatCrawler._crawl_account_albums] Getting albums for: {fakeid} ({account_name})")
        
        try:
            begin = 0
            count = 10
            
            while True:
                result = await self.wechat_client.get_album_list(
                    fakeid=fakeid,
                    begin=begin,
                    count=count
                )
                
                if result.get("base_resp", {}).get("ret") != 0:
                    utils.logger.error(f"[WeChatCrawler._crawl_account_albums] Failed to get albums: {result}")
                    break
                
                albums = result.get("album_list", [])
                
                if not albums:
                    utils.logger.info("[WeChatCrawler._crawl_account_albums] No more albums")
                    break
                
                utils.logger.info(f"[WeChatCrawler._crawl_account_albums] Found {len(albums)} albums")
                
                for album in albums:
                    album_id = album.get("album_id", "")
                    album_title = album.get("title", "Unknown")
                    
                    if not album_id:
                        continue
                    
                    utils.logger.info(
                        f"[WeChatCrawler._crawl_account_albums] Processing album: {album_title} ({album_id})"
                    )
                    
                    await self._crawl_single_album(fakeid, album_id, album_title, account_name)
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                
                # 下一页
                if len(albums) < count:
                    break
                begin += count
                
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._crawl_account_albums] Error: {e}")
    
    async def _crawl_single_album(self, biz: str, album_id: str, album_title: str = "", account_name: str = ""):
        """
        爬取单个合集的所有文章
        
        Args:
            biz: 公众号__biz参数
            album_id: 合集ID
            album_title: 合集标题（可选，用于日志）
            account_name: 公众号名称（可选）
        """
        utils.logger.info(
            f"[WeChatCrawler._crawl_single_album] Crawling album: {album_title or album_id}"
        )
        
        try:
            articles = []
            begin_msgid = ""
            begin_itemidx = ""
            max_articles = getattr(config, "MAX_ARTICLES_PER_ALBUM", 100)
            
            while len(articles) < max_articles:
                result = await self.wechat_client.get_album_articles(
                    biz=biz,
                    album_id=album_id,
                    begin_msgid=begin_msgid,
                    begin_itemidx=begin_itemidx,
                    is_reverse=True,
                    count=20
                )
                
                if result.get("base_resp", {}).get("ret") != 0:
                    utils.logger.error(f"[WeChatCrawler._crawl_single_album] Failed: {result}")
                    break
                
                album_resp = result.get("getalbum_resp", {})
                article_list = album_resp.get("article_list", [])
                
                # 处理单个文章的情况（API有时返回单个对象而非列表）
                if isinstance(article_list, dict):
                    article_list = [article_list]
                
                if not article_list:
                    utils.logger.info("[WeChatCrawler._crawl_single_album] No more articles")
                    break
                
                articles.extend(article_list)
                utils.logger.info(
                    f"[WeChatCrawler._crawl_single_album] Fetched {len(article_list)} articles, "
                    f"total: {len(articles)}"
                )
                
                # 检查是否还有更多
                continue_flag = album_resp.get("continue_flag", "0")
                if continue_flag == "0":
                    break
                
                # 更新分页参数
                last_article = article_list[-1]
                begin_msgid = last_article.get("msgid", "")
                begin_itemidx = last_article.get("itemidx", "")
                
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            
            utils.logger.info(
                f"[WeChatCrawler._crawl_single_album] Total articles in album: {len(articles)}"
            )
            
            # 保存合集文章
            for idx, article in enumerate(articles):
                if idx >= max_articles:
                    break
                
                # 转换为标准文章格式
                article_data = {
                    "aid": article.get("msgid", "") + "_" + article.get("itemidx", ""),
                    "title": article.get("title", ""),
                    "link": article.get("url", ""),
                    "cover": article.get("cover_img_1_1", ""),
                    "digest": "",
                    "create_time": int(article.get("create_time", 0)),
                    "update_time": int(article.get("create_time", 0)),
                    "author": "",
                    "album_id": album_id,
                    "album_title": album_title,
                }
                
                await self.save_article(article_data, biz, account_name)
                
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._crawl_single_album] Error: {e}")

    async def _check_existing_login(self) -> bool:
        """
        检查是否已经登录（用于CDP模式下复用已有登录状态）
        
        Returns:
            True if already logged in, False otherwise
        """
        import re
        from urllib.parse import parse_qs, urlparse
        
        utils.logger.info("[WeChatCrawler._check_existing_login] Checking existing login status...")
        
        try:
            # 获取当前页面URL
            current_url = self.context_page.url
            utils.logger.info(f"[WeChatCrawler._check_existing_login] Current URL: {current_url}")
            
            # 尝试从URL中提取token
            token = None
            parsed = urlparse(current_url)
            params = parse_qs(parsed.query)
            
            if 'token' in params:
                token = params['token'][0]
            else:
                # 尝试正则匹配
                match = re.search(r'token=([^&]+)', current_url)
                if match:
                    token = match.group(1)
            
            if token:
                utils.logger.info(f"[WeChatCrawler._check_existing_login] Found token in URL, already logged in")
                self.wechat_client.set_token(token)
                
                # 输出 Cookie 和 Token 供 WebUI 捕获
                cookies = await self.browser_context.cookies()
                cookie_str, _ = utils.convert_cookies(cookies)
                print(f"[COOKIE_UPDATE] {cookie_str}")
                print(f"[TOKEN_UPDATE] {token}")
                
                return True
            
            # 如果URL中没有token，检查cookies是否包含登录信息
            cookies = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(cookies)
            
            has_data_ticket = bool(cookie_dict.get("data_ticket"))
            has_ticket = bool(cookie_dict.get("ticket"))
            has_data_bizuin = bool(cookie_dict.get("data_bizuin"))
            
            if has_data_ticket or has_ticket or has_data_bizuin:
                utils.logger.info("[WeChatCrawler._check_existing_login] Found login cookies, navigating to get token...")
                
                # 导航到公众号后台首页获取token
                await self.context_page.goto("https://mp.weixin.qq.com/", wait_until="networkidle")
                await asyncio.sleep(2)
                
                # 再次检查URL中的token
                current_url = self.context_page.url
                parsed = urlparse(current_url)
                params = parse_qs(parsed.query)
                
                if 'token' in params:
                    token = params['token'][0]
                    utils.logger.info(f"[WeChatCrawler._check_existing_login] Token extracted after navigation")
                    self.wechat_client.set_token(token)
                    await self.wechat_client.update_cookies(browser_context=self.browser_context)
                    
                    # 输出 Cookie 和 Token 供 WebUI 捕获
                    cookies = await self.browser_context.cookies()
                    cookie_str, _ = utils.convert_cookies(cookies)
                    print(f"[COOKIE_UPDATE] {cookie_str}")
                    print(f"[TOKEN_UPDATE] {token}")
                    
                    return True
            
            utils.logger.info("[WeChatCrawler._check_existing_login] Not logged in, need to login")
            return False
            
        except Exception as e:
            utils.logger.error(f"[WeChatCrawler._check_existing_login] Error checking login: {e}")
            return False

    async def create_wechat_client(self, httpx_proxy: Optional[str]) -> WeChatClient:
        """创建微信客户端"""
        utils.logger.info("[WeChatCrawler.create_wechat_client] Creating WeChat client...")
        
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        
        wechat_client = WeChatClient(
            timeout=60,
            proxy=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Referer": "https://mp.weixin.qq.com/",
                "Origin": "https://mp.weixin.qq.com",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )
        
        return wechat_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True
    ) -> BrowserContext:
        """启动浏览器"""
        utils.logger.info("[WeChatCrawler.launch_browser] Launching browser...")
        
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % "wechat")
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = False
    ) -> BrowserContext:
        """使用CDP模式启动浏览器"""
        utils.logger.info("[WeChatCrawler.launch_browser_with_cdp] Launching browser with CDP...")
        
        from tools.cdp_browser import CDPBrowserManager
        
        self.cdp_manager = CDPBrowserManager()
        
        browser_context = await self.cdp_manager.launch_and_connect(
            playwright=playwright,
            playwright_proxy=playwright_proxy,
            user_agent=user_agent,
            headless=headless,
        )
        
        return browser_context

