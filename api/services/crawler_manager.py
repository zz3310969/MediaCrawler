# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/crawler_manager.py
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
import logging
import subprocess
import signal
import os
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from ..schemas import CrawlerStartRequest, LogEntry

logger = logging.getLogger(__name__)


class CrawlerManager:
    """Crawler process manager"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self.process: Optional[subprocess.Popen] = None
        self.status = "idle"
        self.started_at: Optional[datetime] = None
        self.current_config: Optional[CrawlerStartRequest] = None
        self._log_id = 0
        self._logs: List[LogEntry] = []
        self._read_task: Optional[asyncio.Task] = None
        # Project root directory
        self._project_root = Path(__file__).parent.parent.parent
        # Log queue - for pushing to WebSocket
        self._log_queue: Optional[asyncio.Queue] = None
        # Store new cookies after login
        self.new_cookies: Optional[str] = None
        # Store new token after login
        self.new_token: Optional[str] = None
        # Store new qrcode image (base64)
        self.qrcode_img: Optional[str] = None

    @property
    def logs(self) -> List[LogEntry]:
        return self._logs

    def get_log_queue(self) -> asyncio.Queue:
        """Get or create log queue"""
        if self._log_queue is None:
            self._log_queue = asyncio.Queue()
        return self._log_queue

    def _create_log_entry(self, message: str, level: str = "info") -> LogEntry:
        """Create log entry"""
        self._log_id += 1
        entry = LogEntry(
            id=self._log_id,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message
        )
        self._logs.append(entry)
        # Keep last 500 logs
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]
        return entry

    async def _push_log(self, entry: LogEntry):
        """Push log to queue"""
        if self._log_queue is not None:
            try:
                self._log_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _parse_log_level(self, line: str) -> str:
        """Parse log level"""
        line_upper = line.upper()
        if "ERROR" in line_upper or "FAILED" in line_upper:
            return "error"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            return "warning"
        elif "SUCCESS" in line_upper or "完成" in line or "成功" in line:
            return "success"
        elif "DEBUG" in line_upper:
            return "debug"
        return "info"

    async def start(self, config: CrawlerStartRequest) -> bool:
        """Start crawler process"""
        print(f"[CrawlerManager] Start request received for platform: {config.platform.value}")
        async with self._lock:
            if self.process and self.process.poll() is None:
                print("[CrawlerManager] Process already running")
                return False

            # Clear old logs
            self._logs = []
            self._log_id = 0
            self.new_cookies = None  # Clear old cookies
            self.new_token = None  # Clear old token
            self.qrcode_img = None # Clear old qrcode

            # Clear pending queue (don't replace object to avoid WebSocket broadcast coroutine holding old queue reference)
            if self._log_queue is None:
                self._log_queue = asyncio.Queue()
            else:
                try:
                    while True:
                        self._log_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            # Build command line arguments
            cmd = self._build_command(config)
            print(f"[CrawlerManager] Command: {' '.join(cmd)}")

            # Log start information
            entry = self._create_log_entry(f"Starting crawler: {' '.join(cmd)}", "info")
            await self._push_log(entry)

            try:
                # Start subprocess
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    bufsize=1,
                    cwd=str(self._project_root),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"}
                )
                print(f"[CrawlerManager] Process started, PID: {self.process.pid}")

                self.status = "running"
                self.started_at = datetime.now()
                self.current_config = config

                entry = self._create_log_entry(
                    f"Crawler started on platform: {config.platform.value}, type: {config.crawler_type.value}",
                    "success"
                )
                await self._push_log(entry)

                # Start log reading task
                self._read_task = asyncio.create_task(self._read_output())

                return True
            except Exception as e:
                print(f"[CrawlerManager] Start failed: {e}")
                self.status = "error"
                entry = self._create_log_entry(f"Failed to start crawler: {str(e)}", "error")
                await self._push_log(entry)
                return False

    async def stop(self) -> bool:
        """Stop crawler process"""
        async with self._lock:
            if not self.process or self.process.poll() is not None:
                return False

            self.status = "stopping"
            entry = self._create_log_entry("Sending SIGTERM to crawler process...", "warning")
            await self._push_log(entry)

            try:
                self.process.send_signal(signal.SIGTERM)

                # Wait for graceful exit (up to 15 seconds)
                for _ in range(30):
                    if self.process.poll() is not None:
                        break
                    await asyncio.sleep(0.5)

                # If still not exited, force kill
                if self.process.poll() is None:
                    entry = self._create_log_entry("Process not responding, sending SIGKILL...", "warning")
                    await self._push_log(entry)
                    self.process.kill()

                entry = self._create_log_entry("Crawler process terminated", "info")
                await self._push_log(entry)

            except Exception as e:
                entry = self._create_log_entry(f"Error stopping crawler: {str(e)}", "error")
                await self._push_log(entry)

            self.status = "idle"
            self.current_config = None

            # Cancel log reading task
            if self._read_task:
                self._read_task.cancel()
                self._read_task = None

            return True

    def get_status(self) -> dict:
        """Get current status"""
        return {
            "status": self.status,
            "platform": self.current_config.platform.value if self.current_config else None,
            "crawler_type": self.current_config.crawler_type.value if self.current_config else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error_message": None,
            "new_cookies": self.new_cookies,
            "new_token": self.new_token,
            "qrcode_img": self.qrcode_img
        }

    async def _save_account_from_cookies(self):
        """登录成功后自动创建或更新账号"""
        if not self.current_config or not self.new_cookies:
            return
        try:
            from database.db_session import get_session
            from api.schemas.account import AccountCreate, Platform, LoginMethod, AccountStatus
            from api.services.crud.account import account_crud

            platform = self.current_config.platform.value
            login_type = self.current_config.login_type.value

            async with get_session() as session:
                account = await account_crud.create_account(
                    session,
                    obj_in=AccountCreate(
                        platform=Platform(platform),
                        login_method=LoginMethod(login_type),
                        cookies=self.new_cookies,
                    )
                )
                logger.info(f"[CrawlerManager] Account created: {platform} - {account.account_id}")
                entry = self._create_log_entry(
                    f"账号已自动保存 (ID: {account.account_id})", "success"
                )
                await self._push_log(entry)
        except Exception as e:
            logger.error(f"[CrawlerManager] Failed to save account: {e}")
            entry = self._create_log_entry(f"账号保存失败: {e}", "error")
            await self._push_log(entry)

    def _build_command(self, config: CrawlerStartRequest) -> list:
        """Build main.py command line arguments"""
        cmd = ["uv", "run", "python", "main.py"]

        cmd.extend(["--platform", config.platform.value])
        cmd.extend(["--lt", config.login_type.value])
        cmd.extend(["--type", config.crawler_type.value])
        cmd.extend(["--save_data_option", config.save_option.value])

        # Pass different arguments based on crawler type
        if config.crawler_type.value == "search" and config.keywords:
            cmd.extend(["--keywords", config.keywords])
        elif config.crawler_type.value == "detail" and config.specified_ids:
            cmd.extend(["--specified_id", config.specified_ids])
        elif config.crawler_type.value == "creator" and config.creator_ids:
            cmd.extend(["--creator_id", config.creator_ids])
        elif config.crawler_type.value == "creator_vip" and config.vip_creator_ids:
            cmd.extend(["--vip_creator_id", config.vip_creator_ids])

        if config.start_page != 1:
            cmd.extend(["--start", str(config.start_page)])

        cmd.extend(["--get_comment", "true" if config.enable_comments else "false"])
        cmd.extend(["--get_sub_comment", "true" if config.enable_sub_comments else "false"])

        if config.cookies:
            cmd.extend(["--cookies", config.cookies])

        cmd.extend(["--headless", "true" if config.headless else "false"])
        
        # 增量爬取参数
        if config.enable_incremental:
            cmd.extend(["--enable_incremental", "true"])
            if config.incremental_early_stop != 3:  # 只在非默认值时传递
                cmd.extend(["--incremental_threshold", str(config.incremental_early_stop)])
        
        # 微信专用参数
        if config.platform.value == "wechat":
            if config.wechat_enable_content:
                cmd.extend(["--wechat_enable_content", "true"])
            if config.wechat_enable_reading_stats:
                cmd.extend(["--wechat_enable_stats", "true"])
            if config.wechat_enable_export:
                cmd.extend(["--wechat_enable_export", "true"])
                if config.wechat_export_format:
                    cmd.extend(["--wechat_export_format", config.wechat_export_format])
            if config.wechat_album_ids:
                cmd.extend(["--wechat_album_ids", config.wechat_album_ids])
            if config.wechat_credentials_uin:
                cmd.extend(["--wechat_uin", config.wechat_credentials_uin])
            if config.wechat_credentials_key:
                cmd.extend(["--wechat_key", config.wechat_credentials_key])
            if config.wechat_credentials_pass_ticket:
                cmd.extend(["--wechat_pass_ticket", config.wechat_credentials_pass_ticket])
        
        # 仅登录模式
        if config.login_only:
            cmd.extend(["--login_only", "true"])

        return cmd

    async def _read_output(self):
        """Asynchronously read process output"""
        loop = asyncio.get_event_loop()
        print("[CrawlerManager] Starting output reader loop")

        try:
            while self.process and self.process.poll() is None:
                # Read a line in thread pool
                line = await loop.run_in_executor(
                    None, self.process.stdout.readline
                )
                if line:
                    line = line.strip()
                    if line:
                        print(f"[CrawlerManager] Output: {line[:100]}...")  # Debug print
                        # Check for cookie update
                        if line.startswith("[COOKIE_UPDATE]"):
                            self.new_cookies = line.replace("[COOKIE_UPDATE]", "").strip()
                            # Push raw message for frontend to parse
                            await self._push_log(self._create_log_entry(line, "info"))
                            # Create a success log for display
                            entry = self._create_log_entry("Cookie retrieved successfully", "success")
                            await self._push_log(entry)
                            # login_only 模式下自动创建/更新账号
                            if self.current_config and self.current_config.login_only:
                                await self._save_account_from_cookies()
                        # Check for token update
                        elif line.startswith("[TOKEN_UPDATE]"):
                            self.new_token = line.replace("[TOKEN_UPDATE]", "").strip()
                            # Push raw message for frontend to parse
                            await self._push_log(self._create_log_entry(line, "info"))
                            entry = self._create_log_entry("Token retrieved successfully", "success")
                            await self._push_log(entry)
                        # Check for QR code update
                        elif line.startswith("[QRCODE_UPDATE]"):
                            self.qrcode_img = line.replace("[QRCODE_UPDATE]", "").strip()
                            # Push raw message for frontend to parse
                            await self._push_log(self._create_log_entry(line, "info"))
                            entry = self._create_log_entry("QR Code retrieved successfully", "success")
                            await self._push_log(entry)
                        else:
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line, level)
                            await self._push_log(entry)

            # Read remaining output
            if self.process and self.process.stdout:
                remaining = await loop.run_in_executor(
                    None, self.process.stdout.read
                )
                if remaining:
                    for line in remaining.strip().split('\n'):
                        if line.strip():
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line.strip(), level)
                            await self._push_log(entry)

            # Process ended
            if self.status == "running":
                exit_code = self.process.returncode if self.process else -1
                if exit_code == 0:
                    entry = self._create_log_entry("Crawler completed successfully", "success")
                else:
                    entry = self._create_log_entry(f"Crawler exited with code: {exit_code}", "warning")
                await self._push_log(entry)
                self.status = "idle"

        except asyncio.CancelledError:
            pass
        except Exception as e:
            entry = self._create_log_entry(f"Error reading output: {str(e)}", "error")
            await self._push_log(entry)


# Global singleton
crawler_manager = CrawlerManager()
