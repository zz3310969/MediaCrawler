# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/core.py
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

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : Bilibili Crawler

import asyncio
import os
# import random  # Removed as we now use fixed config.CRAWLER_MAX_SLEEP_SEC intervals
from asyncio import Task
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from crawler.progress import CrawlProgress
from datetime import datetime, timedelta
import pandas as pd

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)
from playwright._impl._errors import TargetClosedError

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        super().__init__()  # 初始化断点续爬相关属性
        self.index_url = "https://www.bilibili.com"
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None
        self.ip_proxy_pool = None  # Proxy IP pool for automatic proxy refresh

    async def start(self):
        # 初始化进度管理器
        self._init_progress_manager()
        
        # 初始化账号池
        await self._init_account_pool("bili")
        
        playwright_proxy_format, httpx_proxy_format = None, None
        
        # 优先使用多账号模式的代理配置
        if self._has_multi_account():
            account = await self._get_next_account()
            if account:
                playwright_proxy_format, httpx_proxy_format = self._get_account_proxy()
                if playwright_proxy_format:
                    utils.logger.info(f"[BilibiliCrawler] Using account proxy: {account.proxy_ip}")
        
        # 如果没有账号代理，使用全局代理池
        if not httpx_proxy_format and config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # Choose launch mode based on configuration
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[BilibiliCrawler] Launching browser using CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[BilibiliCrawler] Launching browser using standard mode")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(chromium, None, self.user_agent, headless=config.HEADLESS)
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.bili_client = await self.create_bilibili_client(httpx_proxy_format)
            if not await self.bili_client.pong():
                # 优先使用账号的Cookie
                cookie_str = self._get_account_cookies() or config.COOKIES
                login_type = config.LOGIN_TYPE
                
                # 如果有账号Cookie，使用cookie登录方式
                if self._current_account and self._current_account.cookies:
                    login_type = "cookie"
                    utils.logger.info(f"[BilibiliCrawler] Using account cookies for login")
                
                login_obj = BilibiliLogin(
                    login_type=login_type,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=cookie_str,
                )
                await login_obj.begin()
                await self.bili_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_videos(config.BILI_SPECIFIED_ID_LIST)
            elif config.CRAWLER_TYPE == "creator":
                if config.CREATOR_MODE:
                    for creator_url in config.BILI_CREATOR_ID_LIST:
                        try:
                            creator_info = parse_creator_info_from_url(creator_url)
                            utils.logger.info(f"[BilibiliCrawler.start] Parsed creator ID: {creator_info.creator_id} from {creator_url}")
                            await self.get_creator_videos(int(creator_info.creator_id))
                        except ValueError as e:
                            utils.logger.error(f"[BilibiliCrawler.start] Failed to parse creator URL: {e}")
                            continue
                else:
                    await self.get_all_creator_details(config.BILI_CREATOR_ID_LIST)
            else:
                pass
            utils.logger.info("[BilibiliCrawler.start] Bilibili Crawler finished ...")

    async def search(self):
        """
        search bilibili video
        """
        # Search for video and retrieve their comment information.
        if config.BILI_SEARCH_MODE == "normal":
            await self.search_by_keywords()
        elif config.BILI_SEARCH_MODE == "all_in_time_range":
            await self.search_by_keywords_in_time_range(daily_limit=False)
        elif config.BILI_SEARCH_MODE == "daily_limit_in_time_range":
            await self.search_by_keywords_in_time_range(daily_limit=True)
        else:
            utils.logger.warning(f"Unknown BILI_SEARCH_MODE: {config.BILI_SEARCH_MODE}")

    @staticmethod
    async def get_pubtime_datetime(
        start: str = config.START_DAY,
        end: str = config.END_DAY,
    ) -> Tuple[str, str]:
        """
        Get bilibili publish start timestamp pubtime_begin_s and publish end timestamp pubtime_end_s
        ---
        :param start: Publish date start time, YYYY-MM-DD
        :param end: Publish date end time, YYYY-MM-DD

        Note
        ---
        - Search time range is from start to end, including both start and end
        - To search content from the same day, to include search content from that day, pubtime_end_s should be pubtime_begin_s plus one day minus one second, i.e., the last second of start day
            - For example, searching only 2024-01-05 content, pubtime_begin_s = 1704384000, pubtime_end_s = 1704470399
              Converted to readable datetime objects: pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0), pubtime_end_s = datetime.datetime(2024, 1, 5, 23, 59, 59)
        - To search content from start to end, to include search content from end day, pubtime_end_s should be pubtime_end_s plus one day minus one second, i.e., the last second of end day
            - For example, searching 2024-01-05 - 2024-01-06 content, pubtime_begin_s = 1704384000, pubtime_end_s = 1704556799
              Converted to readable datetime objects: pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0), pubtime_end_s = datetime.datetime(2024, 1, 6, 23, 59, 59)
        """
        # Convert start and end to datetime objects
        start_day: datetime = datetime.strptime(start, "%Y-%m-%d")
        end_day: datetime = datetime.strptime(end, "%Y-%m-%d")
        if start_day > end_day:
            raise ValueError("Wrong time range, please check your start and end argument, to ensure that the start cannot exceed end")
        elif start_day == end_day:  # Searching content from the same day
            end_day = (start_day + timedelta(days=1) - timedelta(seconds=1))  # Set end_day to start_day + 1 day - 1 second
        else:  # Searching from start to end
            end_day = (end_day + timedelta(days=1) - timedelta(seconds=1))  # Set end_day to end_day + 1 day - 1 second
        # Convert back to timestamps
        return str(int(start_day.timestamp())), str(int(end_day.timestamp()))

    async def search_by_keywords(self):
        """
        search bilibili video with keywords in normal mode
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search_by_keywords] Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < bili_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = bili_limit_count
        
        # 初始化或恢复进度
        keywords_list = [kw.strip() for kw in config.KEYWORDS.split(",") if kw.strip()]
        progress = await self._init_or_resume_progress(
            platform="bili",
            crawler_type="search",
            keywords=keywords_list,
        )
        
        start_page = config.START_PAGE  # start page number
        
        # 从上次的关键词索引开始
        for keyword_idx in range(progress.current_keyword_index, len(keywords_list)):
            keyword = keywords_list[keyword_idx]
            progress.current_keyword_index = keyword_idx
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Current search keyword: {keyword}")
            
            # 从上次的页码开始
            page = progress.current_page if keyword_idx == progress.current_keyword_index else 1
            
            while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Skip page: {page}")
                    page += 1
                    continue

                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] search bilibili keyword: {keyword}, page: {page}")
                progress.current_page = page
                
                video_id_list: List[str] = []
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page,
                    page_size=bili_limit_count,
                    order=SearchOrderType.DEFAULT,
                    pubtime_begin_s=0,  # Publish date start timestamp
                    pubtime_end_s=0,  # Publish date end timestamp
                )
                video_list: List[Dict] = videos_res.get("result")

                if not video_list:
                    utils.logger.info(f"[BilibiliCrawler.search_by_keywords] No more videos for '{keyword}', moving to next keyword.")
                    break

                semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                task_list = []
                try:
                    task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                except Exception as e:
                    utils.logger.warning(f"[BilibiliCrawler.search_by_keywords] error in the task list. The video for this page will not be included. {e}")
                    progress.record_error(str(e))
                video_items = await asyncio.gather(*task_list)
                for video_item in video_items:
                    if video_item:
                        video_aid = str(video_item.get("View").get("aid"))
                        
                        # 跳过已处理的视频
                        if progress.is_note_processed(video_aid):
                            utils.logger.debug(f"[BilibiliCrawler.search_by_keywords] Skip processed video: {video_aid}")
                            continue
                        
                        video_id_list.append(video_aid)
                        await bilibili_store.update_bilibili_video(video_item)
                        await bilibili_store.update_up_info(video_item)
                        await self.get_bilibili_video(video_item, semaphore)
                        
                        # 标记视频已处理
                        progress.mark_note_processed(video_aid)
                        await self._save_progress_if_needed(progress)
                
                page += 1

                # Sleep after page navigation
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")

                await self.batch_get_video_comments(video_id_list, progress)
            
            # 重置页码为下一个关键词
            progress.current_page = 1
        
        # 标记任务完成
        await self._mark_progress_completed(progress)

    async def search_by_keywords_in_time_range(self, daily_limit: bool):
        """
        Search bilibili video with keywords in a given time range.
        :param daily_limit: if True, strictly limit the number of notes per day and total.
        """
        utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Begin search with daily_limit={daily_limit}")
        bili_limit_count = 20
        start_page = config.START_PAGE

        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Current search keyword: {keyword}")
            total_notes_crawled_for_keyword = 0

            for day in pd.date_range(start=config.START_DAY, end=config.END_DAY, freq="D"):
                if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                    utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}', skipping remaining days.")
                    break

                if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                    utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}', skipping remaining days.")
                    break

                pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(start=day.strftime("%Y-%m-%d"), end=day.strftime("%Y-%m-%d"))
                page = 1
                notes_count_this_day = 0

                while True:
                    if notes_count_this_day >= config.MAX_NOTES_PER_DAY:
                        utils.logger.info(f"[BilibiliCrawler.search] Reached MAX_NOTES_PER_DAY limit for {day.ctime()}.")
                        break
                    if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                        utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}'.")
                        break
                    if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                        break

                    try:
                        utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, date: {day.ctime()}, page: {page}")
                        video_id_list: List[str] = []
                        videos_res = await self.bili_client.search_video_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=bili_limit_count,
                            order=SearchOrderType.DEFAULT,
                            pubtime_begin_s=pubtime_begin_s,
                            pubtime_end_s=pubtime_end_s,
                        )
                        video_list: List[Dict] = videos_res.get("result")

                        if not video_list:
                            utils.logger.info(f"[BilibiliCrawler.search] No more videos for '{keyword}' on {day.ctime()}, moving to next day.")
                            break

                        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                        task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                        video_items = await asyncio.gather(*task_list)

                        for video_item in video_items:
                            if video_item:
                                if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                                    break
                                if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                                    break
                                if notes_count_this_day >= config.MAX_NOTES_PER_DAY:
                                    break
                                notes_count_this_day += 1
                                total_notes_crawled_for_keyword += 1
                                video_id_list.append(video_item.get("View").get("aid"))
                                await bilibili_store.update_bilibili_video(video_item)
                                await bilibili_store.update_up_info(video_item)
                                await self.get_bilibili_video(video_item, semaphore)

                        page += 1

                        # Sleep after page navigation
                        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                        utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")

                        await self.batch_get_video_comments(video_id_list)

                    except Exception as e:
                        utils.logger.error(f"[BilibiliCrawler.search] Error searching on {day.ctime()}: {e}")
                        break

    async def batch_get_video_comments(self, video_id_list: List[str], progress: Optional["CrawlProgress"] = None):
        """
        batch get video comments
        :param video_id_list:
        :param progress:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[BilibiliCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        # 过滤已处理评论的视频
        if progress:
            video_id_list = [vid for vid in video_id_list if not progress.is_comment_note_processed(str(vid))]

        utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore, progress), name=str(video_id))
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore, progress: Optional["CrawlProgress"] = None):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :param progress:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_comments] begin get video_id: {video_id} comments ...")
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[BilibiliCrawler.get_comments] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching comments for video {video_id}")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=bilibili_store.batch_update_bilibili_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                
                # 标记评论已处理
                if progress:
                    progress.mark_comment_note_processed(str(video_id))
                    progress.total_comments_crawled += 1
                    await self._save_progress_if_needed(progress)

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_comments] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_comments] may be been blocked, err:{e}")
                # Propagate the exception to be caught by the main loop
                raise

    async def get_creator_videos(self, creator_id: int):
        """
        get videos for a creator - 支持增量爬取
        :return:
        """
        # 初始化增量爬取处理器
        self._init_incremental_handler(platform="bili", crawler_type="creator")
        
        ps = 30
        pn = 1
        all_videos_info = []
        
        # 先获取所有视频信息
        while True:
            result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
            video_list = result.get("list", {}).get("vlist", [])
            all_videos_info.extend(video_list)
            
            if int(result.get("page", {}).get("count", 0)) <= pn * ps:
                break
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {pn}")
            pn += 1
        
        # 🔥 增量过滤：使用早停策略过滤已存在的视频
        video_bvids_list = []
        if self._has_incremental_handler() and all_videos_info:
            # 转换B站视频格式以适配增量处理器
            converted_videos = []
            for video in all_videos_info:
                converted_videos.append({
                    'note_id': str(video.get("bvid", "")),
                    'title': video.get("title", "")[:50],
                    'time': video.get("created", 0),
                })
            
            filtered_converted = await self._incremental_handler.process_creator_notes(
                creator_id=str(creator_id),
                notes_list=converted_videos,
                creator_name=""
            )
            
            # 根据过滤结果筛选视频BV号
            filtered_bvids = {v['note_id'] for v in filtered_converted}
            video_bvids_list = [
                video["bvid"] for video in all_videos_info 
                if video.get("bvid") in filtered_bvids
            ]
            
            # 🔥 更新增量元数据
            if filtered_converted:
                latest_video = filtered_converted[0]
                await self._incremental_handler.update_metadata(
                    creator_id=str(creator_id),
                    latest_note=latest_video,
                    total_new_crawled=len(filtered_converted),
                    creator_name=""
                )
        else:
            # 不使用增量，全部爬取
            video_bvids_list = [video["bvid"] for video in all_videos_info]
        
        # 处理视频列表
        if video_bvids_list:
            await self.get_specified_videos(video_bvids_list)

    async def get_specified_videos(self, video_url_list: List[str], progress: Optional["CrawlProgress"] = None):
        """
        get specified videos info from URLs or BV IDs
        :param video_url_list: List of video URLs or BV IDs
        :param progress: Optional progress object for resume support
        :return:
        """
        utils.logger.info("[BilibiliCrawler.get_specified_videos] Parsing video URLs...")
        
        # 如果没有传入 progress，创建一个新的
        if progress is None:
            bvids_for_progress = []
            for video_url in video_url_list:
                try:
                    video_info = parse_video_info_from_url(video_url)
                    bvids_for_progress.append(video_info.video_id)
                except ValueError:
                    bvids_for_progress.append(video_url)
            
            progress = await self._init_or_resume_progress(
                platform="bili",
                crawler_type="detail",
                note_ids=bvids_for_progress,
            )
        
        bvids_list = []
        for video_url in video_url_list:
            try:
                video_info = parse_video_info_from_url(video_url)
                # 跳过已处理的视频
                if progress.is_note_processed(video_info.video_id):
                    utils.logger.debug(f"[BilibiliCrawler.get_specified_videos] Skip processed video: {video_info.video_id}")
                    continue
                bvids_list.append(video_info.video_id)
                utils.logger.info(f"[BilibiliCrawler.get_specified_videos] Parsed video ID: {video_info.video_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[BilibiliCrawler.get_specified_videos] Failed to parse video URL: {e}")
                progress.record_error(str(e))
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore) for video_id in bvids_list]
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = str(video_item_view.get("aid"))
                video_bvid: str = video_item_view.get("bvid", "")
                if video_aid:
                    video_aids_list.append(video_aid)
                await bilibili_store.update_bilibili_video(video_detail)
                await bilibili_store.update_up_info(video_detail)
                await self.get_bilibili_video(video_detail, semaphore)
                
                # 标记视频已处理
                progress.mark_note_processed(video_bvid or video_aid)
                await self._save_progress_if_needed(progress)
        
        await self.batch_get_video_comments(video_aids_list, progress)
        
        # 标记任务完成
        await self._mark_progress_completed(progress)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)

                # Sleep after fetching video details
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[BilibiliCrawler.get_video_info_task] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching video details {bvid or aid}")

                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None

    async def get_video_play_url_task(self, aid: int, cid: int, semaphore: asyncio.Semaphore) -> Union[Dict, None]:
        """
        Get video play url
        :param aid:
        :param cid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_play_url(aid=aid, cid=cid)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_play_url_task] Get video play url error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_play_url_task] have not fund play url from :{aid}|{cid}, err: {ex}")
                return None

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """
        create bilibili client
        :param httpx_proxy: httpx proxy
        :return: bilibili client
        """
        utils.logger.info("[BilibiliCrawler.create_bilibili_client] Begin create bilibili API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        bilibili_client_obj = BilibiliClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # 传递代理池用于自动刷新
        )
        return bilibili_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        launch browser and create browser context
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        utils.logger.info("[BilibiliCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
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
                channel="chrome",  # Use system's stable Chrome version
            )
            return browser_context
        else:
            # type: ignore
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy, channel="chrome")
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
        Launch browser using CDP mode
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # Display browser information
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[BilibiliCrawler] CDP browser info: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler] CDP mode launch failed, fallback to standard mode: {e}")
            # Fallback to standard mode
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        """Close browser context"""
        # 保存进度
        await self._save_progress_on_close()
        
        # 保存账号池状态
        await self._save_account_pool_on_close()
        
        try:
            # If using CDP mode, special handling is required
            if self.cdp_manager:
                await self.cdp_manager.cleanup()
                self.cdp_manager = None
            elif self.browser_context:
                await self.browser_context.close()
            utils.logger.info("[BilibiliCrawler.close] Browser context closed ...")
        except TargetClosedError:
            utils.logger.warning("[BilibiliCrawler.close] Browser context was already closed.")
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.close] An error occurred during close: {e}")

    async def get_bilibili_video(self, video_item: Dict, semaphore: asyncio.Semaphore):
        """
        download bilibili video
        :param video_item:
        :param semaphore:
        :return:
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Crawling image mode is not enabled")
            return
        video_item_view: Dict = video_item.get("View")
        aid = video_item_view.get("aid")
        cid = video_item_view.get("cid")
        result = await self.get_video_play_url_task(aid, cid, semaphore)
        if result is None:
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video play url failed")
            return
        durl_list = result.get("durl")
        max_size = -1
        video_url = ""
        for durl in durl_list:
            size = durl.get("size")
            if size > max_size:
                max_size = size
                video_url = durl.get("url")
        if video_url == "":
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video url failed")
            return

        content = await self.bili_client.get_video_media(video_url)
        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
        utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching video {aid}")
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await bilibili_store.store_video(aid, content, extension_file_name)

    async def get_all_creator_details(self, creator_url_list: List[str]):
        """
        creator_url_list: get details for creator from creator URL list
        """
        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Crawling the details of creators")
        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Parsing creator URLs...")

        creator_id_list = []
        for creator_url in creator_url_list:
            try:
                creator_info = parse_creator_info_from_url(creator_url)
                creator_id_list.append(int(creator_info.creator_id))
                utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Parsed creator ID: {creator_info.creator_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[BilibiliCrawler.get_all_creator_details] Failed to parse creator URL: {e}")
                continue

        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] creator ids:{creator_id_list}")

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        try:
            for creator_id in creator_id_list:
                task = asyncio.create_task(self.get_creator_details(creator_id, semaphore), name=str(creator_id))
                task_list.append(task)
        except Exception as e:
            utils.logger.warning(f"[BilibiliCrawler.get_all_creator_details] error in the task list. The creator will not be included. {e}")

        await asyncio.gather(*task_list)

    async def get_creator_details(self, creator_id: int, semaphore: asyncio.Semaphore):
        """
        get details for creator id
        :param creator_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
            creator_info: Dict = {
                "id": creator_id,
                "name": creator_unhandled_info.get("name"),
                "sign": creator_unhandled_info.get("sign"),
                "avatar": creator_unhandled_info.get("face"),
            }
        await self.get_fans(creator_info, semaphore)
        await self.get_followings(creator_info, semaphore)
        await self.get_dynamics(creator_info, semaphore)

    async def get_fans(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get fans for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_fans] begin get creator_id: {creator_id} fans ...")
                await self.bili_client.get_creator_all_fans(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_fans,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_fans] get creator_id: {creator_id} fans error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_fans] may be been blocked, err:{e}")

    async def get_followings(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get followings for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_followings] begin get creator_id: {creator_id} followings ...")
                await self.bili_client.get_creator_all_followings(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_followings,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_followings] get creator_id: {creator_id} followings error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_followings] may be been blocked, err:{e}")

    async def get_dynamics(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get dynamics for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_dynamics] begin get creator_id: {creator_id} dynamics ...")
                await self.bili_client.get_creator_all_dynamics(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_dynamics,
                    max_count=config.CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_dynamics] get creator_id: {creator_id} dynamics error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_dynamics] may be been blocked, err:{e}")
