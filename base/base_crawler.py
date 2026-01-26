# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/base/base_crawler.py
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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType, Playwright

import config
from tools import utils

if TYPE_CHECKING:
    from account.account_pool import Account, AccountPool
    from crawler.progress import CrawlProgress, ProgressManager


class AbstractCrawler(ABC):
    """
    爬虫抽象基类
    提供断点续爬、多账号管理等通用功能的默认实现
    """
    
    def __init__(self):
        # 断点续爬相关属性
        self._progress_manager: Optional["ProgressManager"] = None
        self._current_progress: Optional["CrawlProgress"] = None
        self._progress_save_counter: int = 0
        
        # 多账号相关属性
        self._account_pool: Optional["AccountPool"] = None
        self._current_account: Optional["Account"] = None
        self._consecutive_failures: int = 0
    
    def _init_progress_manager(self) -> None:
        """
        初始化进度管理器（在子类的 start() 方法开始时调用）
        """
        if config.ENABLE_RESUME_CRAWL:
            from crawler.progress import ProgressManager
            self._progress_manager = ProgressManager(config.PROGRESS_DIR)
    
    async def _init_or_resume_progress(
        self,
        platform: str,
        crawler_type: str,
        keywords: Optional[List[str]] = None,
        creator_ids: Optional[List[str]] = None,
        vip_creator_ids: Optional[List[str]] = None,
        note_ids: Optional[List[str]] = None,
    ) -> "CrawlProgress":
        """
        初始化或恢复爬取进度（通用实现）
        :param platform: 平台标识 (wb, xhs, dy, etc.)
        :param crawler_type: 爬取类型 (search, detail, creator, creator_vip)
        :param keywords: 关键词列表
        :param creator_ids: 创作者ID列表
        :param vip_creator_ids: VIP创作者ID列表
        :param note_ids: 帖子ID列表
        :return: 进度对象
        """
        from crawler.progress import CrawlProgress, CrawlStatus
        
        # 如果未启用断点续爬，创建新进度
        if not config.ENABLE_RESUME_CRAWL or not self._progress_manager:
            progress = CrawlProgress(
                platform=platform,
                crawler_type=crawler_type,
                keywords=keywords or [],
                creator_ids=creator_ids or [],
                vip_creator_ids=vip_creator_ids or [],
                note_ids=note_ids or [],
            )
            progress.status = CrawlStatus.RUNNING.value
            self._current_progress = progress
            return progress
        
        # 尝试恢复上次未完成的任务
        if config.AUTO_RESUME_LAST_TASK:
            existing_progress = await self._progress_manager.load_latest_unfinished(platform, crawler_type)
            if existing_progress:
                # 验证任务参数是否匹配
                params_match = self._check_progress_params_match(
                    existing_progress, keywords, creator_ids, vip_creator_ids, note_ids
                )
                if params_match:
                    utils.logger.info(f"[{self.__class__.__name__}] Resuming previous task: {existing_progress.task_id}")
                    utils.logger.info(f"[{self.__class__.__name__}] Progress: {existing_progress.total_notes_crawled} notes crawled")
                    existing_progress.status = CrawlStatus.RUNNING.value
                    await self._progress_manager.save_progress(existing_progress)
                    self._current_progress = existing_progress
                    return existing_progress
                else:
                    utils.logger.info(f"[{self.__class__.__name__}] Previous task parameters don't match, starting new task")
        
        # 创建新进度
        progress = CrawlProgress(
            platform=platform,
            crawler_type=crawler_type,
            keywords=keywords or [],
            creator_ids=creator_ids or [],
            vip_creator_ids=vip_creator_ids or [],
            note_ids=note_ids or [],
        )
        progress.status = CrawlStatus.RUNNING.value
        await self._progress_manager.save_progress(progress)
        self._current_progress = progress
        
        utils.logger.info(f"[{self.__class__.__name__}] Created new task: {progress.task_id}")
        return progress
    
    def _check_progress_params_match(
        self,
        progress: "CrawlProgress",
        keywords: Optional[List[str]],
        creator_ids: Optional[List[str]],
        vip_creator_ids: Optional[List[str]],
        note_ids: Optional[List[str]],
    ) -> bool:
        """
        检查进度参数是否与当前配置匹配
        """
        if progress.crawler_type == "search":
            return progress.keywords == (keywords or [])
        elif progress.crawler_type == "creator":
            return progress.creator_ids == (creator_ids or [])
        elif progress.crawler_type == "creator_vip":
            return progress.vip_creator_ids == (vip_creator_ids or [])
        elif progress.crawler_type == "detail":
            return progress.note_ids == (note_ids or [])
        return False
    
    async def _save_progress_if_needed(self, progress: "CrawlProgress", force: bool = False) -> None:
        """
        根据配置的间隔保存进度
        :param progress: 进度对象
        :param force: 是否强制保存
        """
        if not config.ENABLE_RESUME_CRAWL or not self._progress_manager:
            return
        
        self._progress_save_counter += 1
        
        if force or self._progress_save_counter >= config.PROGRESS_SAVE_INTERVAL:
            await self._progress_manager.save_progress(progress)
            self._progress_save_counter = 0
            utils.logger.debug(f"[{self.__class__.__name__}] Progress saved: {progress.total_notes_crawled} notes")
    
    async def _mark_progress_completed(self, progress: "CrawlProgress") -> None:
        """
        标记进度为完成状态
        """
        if not config.ENABLE_RESUME_CRAWL or not self._progress_manager:
            return
        
        await self._progress_manager.mark_completed(progress)
        utils.logger.info(f"[{self.__class__.__name__}] Task completed: {progress.task_id}")
        utils.logger.info(f"[{self.__class__.__name__}] Total notes: {progress.total_notes_crawled}, comments: {progress.total_comments_crawled}")
        
        # 清理旧的进度文件
        if config.CLEANUP_OLD_PROGRESS:
            deleted = await self._progress_manager.cleanup_completed(config.PROGRESS_KEEP_DAYS)
            if deleted > 0:
                utils.logger.info(f"[{self.__class__.__name__}] Cleaned up {deleted} old progress files")
    
    async def _save_progress_on_close(self) -> None:
        """
        关闭时保存进度（在子类的 close() 方法中调用）
        """
        from crawler.progress import CrawlStatus
        
        if self._current_progress and self._progress_manager:
            if self._current_progress.status == CrawlStatus.RUNNING.value:
                self._current_progress.status = CrawlStatus.PAUSED.value
                await self._progress_manager.save_progress(self._current_progress)
                utils.logger.info(f"[{self.__class__.__name__}] Progress saved on close: {self._current_progress.task_id}")
    
    # ==================== 多账号管理方法 ====================
    
    async def _init_account_pool(self, platform: str) -> None:
        """
        初始化账号池（在子类的 start() 方法中调用）
        
        Args:
            platform: 平台标识 (xhs, dy, wb, etc.)
        """
        if not config.ENABLE_MULTI_ACCOUNT:
            return
        
        from account.account_pool import create_account_pool
        
        self._account_pool = await create_account_pool(
            platform=platform,
            accounts_dir=config.ACCOUNTS_DIR,
            rotation_strategy=config.ACCOUNT_ROTATION_STRATEGY
        )
        
        if self._account_pool.has_accounts():
            utils.logger.info(
                f"[{self.__class__.__name__}] Account pool initialized: "
                f"{len(self._account_pool.accounts)} accounts loaded"
            )
            stats = self._account_pool.get_stats()
            utils.logger.info(
                f"[{self.__class__.__name__}] Available: {stats['available_accounts']}, "
                f"Cooling: {stats['cooling_accounts']}, Banned: {stats['banned_accounts']}"
            )
        else:
            utils.logger.warning(
                f"[{self.__class__.__name__}] No accounts found in pool, "
                f"will use default login method"
            )
    
    async def _get_next_account(self) -> Optional["Account"]:
        """
        获取下一个可用账号
        
        Returns:
            Account: 账号对象，如果没有可用账号则返回None
        """
        if not self._account_pool:
            return None
        
        account = await self._account_pool.get_next_account()
        if account:
            self._current_account = account
            self._consecutive_failures = 0
            utils.logger.info(
                f"[{self.__class__.__name__}] Switched to account: {account.account_id}"
            )
        return account
    
    async def _report_account_success(self) -> None:
        """报告当前账号请求成功"""
        if self._account_pool and self._current_account:
            await self._account_pool.report_success(self._current_account.account_id)
            self._consecutive_failures = 0
    
    async def _report_account_failure(self, error: str = "") -> None:
        """
        报告当前账号请求失败
        
        Args:
            error: 错误信息
        """
        if not self._account_pool or not self._current_account:
            return
        
        await self._account_pool.report_failure(self._current_account.account_id, error)
        self._consecutive_failures += 1
        
        # 检查是否需要标记为冷却
        if self._consecutive_failures >= config.MAX_CONSECUTIVE_FAILURES:
            await self._report_account_rate_limited()
    
    async def _report_account_rate_limited(self) -> None:
        """报告当前账号被限流"""
        if not self._account_pool or not self._current_account:
            return
        
        await self._account_pool.report_rate_limited(
            self._current_account.account_id,
            config.ACCOUNT_COOLING_MINUTES
        )
        utils.logger.warning(
            f"[{self.__class__.__name__}] Account {self._current_account.account_id} "
            f"marked as rate-limited, cooling for {config.ACCOUNT_COOLING_MINUTES} minutes"
        )
        
        # 如果配置了自动切换，尝试切换到下一个账号
        if config.AUTO_SWITCH_ON_RATE_LIMIT:
            await self._switch_to_next_account()
    
    async def _report_account_banned(self) -> None:
        """报告当前账号被封禁"""
        if self._account_pool and self._current_account:
            await self._account_pool.report_banned(self._current_account.account_id)
            utils.logger.error(
                f"[{self.__class__.__name__}] Account {self._current_account.account_id} banned!"
            )
            # 尝试切换到下一个账号
            await self._switch_to_next_account()
    
    async def _report_account_invalid(self) -> None:
        """报告当前账号登录失效"""
        if self._account_pool and self._current_account:
            await self._account_pool.report_invalid(self._current_account.account_id)
            utils.logger.warning(
                f"[{self.__class__.__name__}] Account {self._current_account.account_id} "
                f"login expired, need re-login"
            )
    
    async def _switch_to_next_account(self) -> bool:
        """
        切换到下一个可用账号
        
        Returns:
            bool: 是否成功切换
        """
        if not self._account_pool:
            return False
        
        if not self._account_pool.has_available_accounts():
            utils.logger.error(
                f"[{self.__class__.__name__}] No available accounts left in pool!"
            )
            return False
        
        new_account = await self._get_next_account()
        if new_account:
            utils.logger.info(
                f"[{self.__class__.__name__}] Switched to new account: {new_account.account_id}"
            )
            return True
        return False
    
    def _get_account_cookies(self) -> Optional[str]:
        """
        获取当前账号的Cookie字符串
        
        Returns:
            str: Cookie字符串，如果没有当前账号则返回None
        """
        if self._current_account and self._current_account.cookies:
            return self._current_account.cookies
        return None
    
    def _get_account_browser_dir(self) -> Optional[str]:
        """
        获取当前账号的浏览器数据目录
        
        Returns:
            str: 浏览器数据目录路径，如果没有则返回None
        """
        if self._current_account and self._current_account.browser_data_dir:
            return self._current_account.browser_data_dir
        return None
    
    def _get_account_proxy(self) -> tuple[Optional[Dict], Optional[str]]:
        """
        获取当前账号绑定的代理配置
        
        Returns:
            tuple: (playwright_proxy, httpx_proxy) 如果账号没有绑定代理则返回 (None, None)
        """
        if not self._current_account:
            return None, None
        
        playwright_proxy = self._current_account.get_playwright_proxy()
        httpx_proxy = self._current_account.get_proxy_url()
        
        return playwright_proxy, httpx_proxy
    
    def _has_multi_account(self) -> bool:
        """检查是否启用了多账号模式且有可用账号"""
        return (
            config.ENABLE_MULTI_ACCOUNT and 
            self._account_pool is not None and 
            self._account_pool.has_accounts()
        )
    
    async def _save_account_pool_on_close(self) -> None:
        """关闭时保存账号池状态"""
        if self._account_pool:
            await self._account_pool.save_accounts()
            utils.logger.info(f"[{self.__class__.__name__}] Account pool saved on close")

    @abstractmethod
    async def start(self):
        """
        start crawler
        """
        pass

    @abstractmethod
    async def search(self):
        """
        search
        """
        pass

    @abstractmethod
    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        launch browser
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        pass

    async def launch_browser_with_cdp(self, playwright: Playwright, playwright_proxy: Optional[Dict], user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        Launch browser using CDP mode (optional implementation)
        :param playwright: playwright instance
        :param playwright_proxy: playwright proxy configuration
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        # Default implementation: fallback to standard mode
        return await self.launch_browser(playwright.chromium, playwright_proxy, user_agent, headless)


class AbstractLogin(ABC):

    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def login_by_qrcode(self):
        pass

    @abstractmethod
    async def login_by_mobile(self):
        pass

    @abstractmethod
    async def login_by_cookies(self):
        pass


class AbstractStore(ABC):

    @abstractmethod
    async def store_content(self, content_item: Dict):
        pass

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        pass

    # TODO support all platform
    # only xhs is supported, so @abstractmethod is commented
    @abstractmethod
    async def store_creator(self, creator: Dict):
        pass


class AbstractStoreImage(ABC):
    # TODO: support all platform
    # only weibo is supported
    # @abstractmethod
    async def store_image(self, image_content_item: Dict):
        pass


class AbstractStoreVideo(ABC):
    # TODO: support all platform
    # only weibo is supported
    # @abstractmethod
    async def store_video(self, video_content_item: Dict):
        pass


class AbstractApiClient(ABC):

    @abstractmethod
    async def request(self, method, url, **kwargs):
        pass

    @abstractmethod
    async def update_cookies(self, browser_context: BrowserContext):
        pass
