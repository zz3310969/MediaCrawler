# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/core.py
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
import random
from asyncio import Task
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from crawler.progress import CrawlProgress

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import DouYinClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    context_page: Page
    dy_client: DouYinClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        super().__init__()  # 初始化断点续爬相关属性
        self.index_url = "https://www.douyin.com"
        self.cdp_manager = None
        self.ip_proxy_pool = None  # 代理IP池，用于代理自动刷新

    async def start(self) -> None:
        # 初始化进度管理器
        self._init_progress_manager()
        
        # 初始化账号池
        await self._init_account_pool("dy")
        
        playwright_proxy_format, httpx_proxy_format = None, None
        
        # 优先使用多账号模式的代理配置
        if self._has_multi_account():
            account = await self._get_next_account()
            if account:
                playwright_proxy_format, httpx_proxy_format = self._get_account_proxy()
                if playwright_proxy_format:
                    utils.logger.info(f"[DouYinCrawler] Using account proxy: {account.proxy_ip}")
        
        # 如果没有账号代理，使用全局代理池
        if not httpx_proxy_format and config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                # 优先使用账号的Cookie
                cookie_str = self._get_account_cookies() or config.COOKIES
                login_type = config.LOGIN_TYPE
                
                # 如果有账号Cookie，使用cookie登录方式
                if self._current_account and self._current_account.cookies:
                    login_type = "cookie"
                    utils.logger.info(f"[DouYinCrawler] Using account cookies for login")
                
                login_obj = DouYinLogin(
                    login_type=login_type,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=cookie_str,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)

                current_cookie = await self.browser_context.cookies()
                cookie_str_out, _ = utils.convert_cookies(current_cookie)
                if cookie_str_out:
                    print(f"[COOKIE_UPDATE] {cookie_str_out}")

            login_only = getattr(config, 'LOGIN_ONLY', False)
            if login_only:
                utils.logger.info("[DouYinCrawler] Login only mode - skipping crawling")
                return

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        
        # 初始化或恢复进度
        keywords_list = [kw.strip() for kw in config.KEYWORDS.split(",") if kw.strip()]
        progress = await self._init_or_resume_progress(
            platform="dy",
            crawler_type="search",
            keywords=keywords_list,
        )
        
        start_page = config.START_PAGE  # start page number
        
        # 从上次的关键词索引开始
        for keyword_idx in range(progress.current_keyword_index, len(keywords_list)):
            keyword = keywords_list[keyword_idx]
            progress.current_keyword_index = keyword_idx
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            
            # 从上次的页码开始
            page = progress.current_page if keyword_idx == progress.current_keyword_index else 0
            dy_search_id = ""
            
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    progress.current_page = page
                    
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit_count - dy_limit_count,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError as e:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    progress.record_error(str(e))
                    await self._save_progress_if_needed(progress, force=True)
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                page_aweme_list = []
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = (post_item.get("aweme_info") or post_item.get("aweme_mix_info", {}).get("mix_items")[0])
                    except TypeError:
                        continue
                    aweme_id = aweme_info.get("aweme_id", "")
                    
                    # 跳过已处理的视频
                    if progress.is_note_processed(aweme_id):
                        utils.logger.debug(f"[DouYinCrawler.search] Skip processed aweme: {aweme_id}")
                        continue
                    
                    aweme_list.append(aweme_id)
                    page_aweme_list.append(aweme_id)
                    await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
                    await self.get_aweme_media(aweme_item=aweme_info)
                    
                    # 标记视频已处理
                    progress.mark_note_processed(aweme_id)
                    await self._save_progress_if_needed(progress)
                
                # Batch get note comments for the current page
                await self.batch_get_note_comments(page_aweme_list, progress)

                # Sleep after each page navigation
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.search] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")
            
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")
            # 重置页码为下一个关键词
            progress.current_page = 0
        
        # 标记任务完成
        await self._mark_progress_completed(progress)

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post from URLs or IDs"""
        utils.logger.info("[DouYinCrawler.get_specified_awemes] Parsing video URLs...")
        
        # 先解析所有视频ID
        all_aweme_ids = []
        for video_url in config.DY_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)
                if video_info.url_type == "short":
                    # 短链接需要在运行时解析，先跳过
                    all_aweme_ids.append(video_url)  # 暂存URL
                else:
                    all_aweme_ids.append(video_info.aweme_id)
            except ValueError:
                all_aweme_ids.append(video_url)
        
        # 初始化或恢复进度
        progress = await self._init_or_resume_progress(
            platform="dy",
            crawler_type="detail",
            note_ids=all_aweme_ids,
        )
        
        aweme_id_list = []
        for video_url in config.DY_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)

                # 处理短链接
                if video_info.url_type == "short":
                    utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.dy_client.resolve_short_url(video_url)
                    if resolved_url:
                        # 从解析后的URL中提取视频ID
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Short link resolved to aweme ID: {video_info.aweme_id}")
                    else:
                        utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to resolve short link: {video_url}")
                        continue

                aweme_id = video_info.aweme_id
                
                # 跳过已处理的视频
                if progress.is_note_processed(aweme_id):
                    utils.logger.debug(f"[DouYinCrawler.get_specified_awemes] Skip processed aweme: {aweme_id}")
                    continue
                
                aweme_id_list.append(aweme_id)
                utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Parsed aweme ID: {aweme_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                progress.record_error(str(e))
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in aweme_id_list]
        aweme_details = await asyncio.gather(*task_list)
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                aweme_id = aweme_detail.get("aweme_id", "")
                await douyin_store.update_douyin_aweme(aweme_item=aweme_detail)
                await self.get_aweme_media(aweme_item=aweme_detail)
                
                # 标记视频已处理
                progress.mark_note_processed(aweme_id)
                await self._save_progress_if_needed(progress)
        
        await self.batch_get_note_comments(aweme_id_list, progress)
        
        # 标记任务完成
        await self._mark_progress_completed(progress)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                result = await self.dy_client.get_video_by_id(aweme_id)
                # Sleep after fetching aweme detail
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.get_aweme_detail] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching aweme {aweme_id}")
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str], progress: Optional["CrawlProgress"] = None) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        # 过滤已处理评论的视频
        if progress:
            aweme_list = [aid for aid in aweme_list if not progress.is_comment_note_processed(aid)]

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore, progress), name=aweme_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore, progress: Optional["CrawlProgress"] = None) -> None:
        async with semaphore:
            try:
                # 将关键词列表传递给 get_aweme_all_comments 方法
                # Use fixed crawling interval
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=douyin_store.batch_update_dy_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                
                # 标记评论已处理
                if progress:
                    progress.mark_comment_note_processed(aweme_id)
                    progress.total_comments_crawled += 1
                    await self._save_progress_if_needed(progress)
                
                # Sleep after fetching comments
                await asyncio.sleep(crawl_interval)
                utils.logger.info(f"[DouYinCrawler.get_comments] Sleeping for {crawl_interval} seconds after fetching comments for aweme {aweme_id}")
                utils.logger.info(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator from URLs or IDs
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Parsing creator URLs...")

        # 初始化或恢复进度
        progress = await self._init_or_resume_progress(
            platform="dy",
            crawler_type="creator",
            creator_ids=config.DY_CREATOR_ID_LIST,
        )
        
        # 初始化增量爬取处理器
        self._init_incremental_handler(platform="dy", crawler_type="creator")

        # 从上次的创作者索引开始
        for creator_idx in range(progress.current_creator_index, len(config.DY_CREATOR_ID_LIST)):
            creator_url = config.DY_CREATOR_ID_LIST[creator_idx]
            progress.current_creator_index = creator_idx
            
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                user_id = creator_info_parsed.sec_user_id
                utils.logger.info(f"[DouYinCrawler.get_creators_and_videos] Parsed sec_user_id: {user_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                progress.record_error(str(e))
                continue

            creator_info: Dict = await self.dy_client.get_user_info(user_id)
            creator_name = ""
            if creator_info:
                await douyin_store.save_creator(user_id, creator=creator_info)
                creator_name = creator_info.get("nickname", "")

            # Get all video information of the creator (不使用callback，先获取全部)
            all_video_list = await self.dy_client.get_all_user_aweme_posts(
                sec_user_id=user_id, 
                callback=None  # 先不处理，等增量过滤后再处理
            )
            
            # 🔥 增量过滤：使用早停策略过滤已存在的视频
            if self._has_incremental_handler():
                # 转换抖音视频格式以适配增量处理器
                converted_videos = []
                for video in all_video_list:
                    converted_videos.append({
                        'note_id': str(video.get("aweme_id", "")),
                        'title': video.get("desc", "")[:50],
                        'time': video.get("create_time", 0),
                    })
                
                filtered_converted = await self._incremental_handler.process_creator_notes(
                    creator_id=user_id,
                    notes_list=converted_videos,
                    creator_name=creator_name
                )
                
                # 根据过滤结果筛选原始视频
                filtered_video_ids = {v['note_id'] for v in filtered_converted}
                all_video_list = [
                    video for video in all_video_list 
                    if str(video.get("aweme_id", "")) in filtered_video_ids
                ]
            
            # 处理过滤后的视频
            if all_video_list:
                await self.fetch_creator_video_detail(all_video_list)

            video_ids = []
            for video_item in all_video_list:
                video_id = video_item.get("aweme_id")
                video_ids.append(video_id)
                progress.mark_note_processed(video_id)
            
            # 🔥 更新增量元数据
            if self._has_incremental_handler() and all_video_list:
                latest_video = all_video_list[0]
                latest_note = {
                    'note_id': str(latest_video.get("aweme_id", "")),
                    'title': latest_video.get("desc", "")[:50],
                    'time': latest_video.get("create_time", 0),
                }
                await self._incremental_handler.update_metadata(
                    creator_id=user_id,
                    latest_note=latest_note,
                    total_new_crawled=len(all_video_list),
                    creator_name=creator_name
                )
            
            await self.batch_get_note_comments(video_ids, progress)
            await self._save_progress_if_needed(progress, force=True)
        
        # 标记任务完成
        await self._mark_progress_completed(progress)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list]

        note_details = await asyncio.gather(*task_list)
        for aweme_item in note_details:
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_item)
                await self.get_aweme_media(aweme_item=aweme_item)

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        douyin_client = DouYinClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # 传递代理池用于自动刷新
        )
        return douyin_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # 添加反检测脚本
            await self.cdp_manager.add_stealth_script()

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        # 保存进度
        await self._save_progress_on_close()
        
        # 保存账号池状态
        await self._save_account_pool_on_close()
        
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        """
        获取抖音媒体，自动判断媒体类型是短视频还是帖子图片并下载

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[DouYinCrawler.get_aweme_media] Crawling image mode is not enabled")
            return
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)
        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)
        # TODO: 抖音并没采用音视频分离的策略，故音频可从原视频中分离，暂不提取
        if note_download_url:
            await self.get_aweme_images(aweme_item)
        else:
            await self.get_aweme_video(aweme_item)

    async def get_aweme_images(self, aweme_item: Dict):
        """
        get aweme images. please use get_aweme_media

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)

        if not note_download_url:
            return
        picNum = 0
        for url in note_download_url:
            if not url:
                continue
            content = await self.dy_client.get_aweme_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            extension_file_name = f"{picNum:>03d}.jpeg"
            picNum += 1
            await douyin_store.update_dy_aweme_image(aweme_id, content, extension_file_name)

    async def get_aweme_video(self, aweme_item: Dict):
        """
        get aweme videos. please use get_aweme_media

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")

        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)

        if not video_download_url:
            return
        content = await self.dy_client.get_aweme_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await douyin_store.update_dy_aweme_video(aweme_id, content, extension_file_name)
