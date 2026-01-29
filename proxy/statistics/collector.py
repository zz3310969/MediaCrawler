# -*- coding: utf-8 -*-
# @Desc    : 代理使用统计收集器

import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from tools.utils import utils

from ..types import ProxyUsageRecord, ProxyDailyStats
from .store import StatisticsStore


class ProxyStatisticsCollector:
    """
    代理使用统计收集器
    
    功能:
    - 收集每个请求的使用记录
    - 批量保存到存储
    - 实时统计
    """
    
    def __init__(
        self,
        store: StatisticsStore,
        batch_size: int = 100,
        flush_interval_seconds: float = 60,
    ):
        """
        初始化收集器
        
        Args:
            store: 统计存储
            batch_size: 批量保存大小
            flush_interval_seconds: 自动刷新间隔（秒）
        """
        self._store = store
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        
        # 待保存的记录缓冲
        self._buffer: List[ProxyUsageRecord] = []
        self._buffer_lock = asyncio.Lock()
        
        # 实时统计（今日）
        self._today_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "accounts": set(),
            "platforms": set(),
        })
        self._today_date: str = datetime.now().strftime("%Y-%m-%d")
        
        # 后台刷新任务
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动收集器"""
        self._running = True
        self._flush_task = asyncio.create_task(self._auto_flush_loop())
        utils.logger.info("[StatisticsCollector] Started")
    
    async def stop(self) -> None:
        """停止收集器"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 刷新剩余数据
        await self.flush()
        utils.logger.info("[StatisticsCollector] Stopped")
    
    async def _auto_flush_loop(self) -> None:
        """自动刷新循环"""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            try:
                await self.flush()
            except Exception as e:
                utils.logger.error(f"[StatisticsCollector] Auto flush failed: {e}")
    
    async def record(
        self,
        proxy_id: str,
        platform: str,
        success: bool,
        response_time_ms: float = 0,
        account_id: Optional[str] = None,
        request_url: Optional[str] = None,
        request_method: str = "GET",
        response_code: Optional[int] = None,
        bytes_sent: int = 0,
        bytes_received: int = 0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        记录一次请求
        
        Args:
            proxy_id: 代理ID
            platform: 平台
            success: 是否成功
            response_time_ms: 响应时间（毫秒）
            account_id: 账号ID
            request_url: 请求URL
            request_method: 请求方法
            response_code: 响应状态码
            bytes_sent: 发送字节数
            bytes_received: 接收字节数
            error_type: 错误类型
            error_message: 错误信息
        """
        record = ProxyUsageRecord(
            record_id=str(uuid.uuid4()),
            proxy_id=proxy_id,
            account_id=account_id,
            platform=platform,
            request_url=request_url,
            request_method=request_method,
            response_code=response_code,
            response_time_ms=response_time_ms,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            success=success,
            error_type=error_type,
            error_message=error_message,
            created_at=datetime.now(),
        )
        
        # 添加到缓冲
        async with self._buffer_lock:
            self._buffer.append(record)
            
            # 检查是否需要刷新
            if len(self._buffer) >= self._batch_size:
                await self._flush_buffer()
        
        # 更新实时统计
        self._update_realtime_stats(record)
    
    def _update_realtime_stats(self, record: ProxyUsageRecord) -> None:
        """更新实时统计"""
        # 检查日期是否变化
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today_date:
            self._today_stats.clear()
            self._today_date = today
        
        stats = self._today_stats[record.proxy_id]
        stats["total_requests"] += 1
        if record.success:
            stats["success_requests"] += 1
            stats["total_response_time"] += record.response_time_ms
        else:
            stats["failed_requests"] += 1
        
        stats["total_bytes_sent"] += record.bytes_sent
        stats["total_bytes_received"] += record.bytes_received
        
        if record.account_id:
            stats["accounts"].add(record.account_id)
        stats["platforms"].add(record.platform)
    
    async def flush(self) -> None:
        """刷新缓冲区到存储"""
        async with self._buffer_lock:
            await self._flush_buffer()
    
    async def _flush_buffer(self) -> None:
        """内部刷新方法"""
        if not self._buffer:
            return
        
        records = self._buffer
        self._buffer = []
        
        try:
            saved = await self._store.save_usage_records(records)
            utils.logger.debug(
                f"[StatisticsCollector] Flushed {saved}/{len(records)} records"
            )
        except Exception as e:
            utils.logger.error(f"[StatisticsCollector] Failed to save records: {e}")
            # 失败时将记录放回缓冲
            async with self._buffer_lock:
                self._buffer = records + self._buffer
    
    def get_realtime_stats(self, proxy_id: str) -> Dict:
        """
        获取代理的实时统计（今日）
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            统计数据
        """
        stats = self._today_stats.get(proxy_id, {})
        total = stats.get("total_requests", 0)
        success = stats.get("success_requests", 0)
        
        return {
            "proxy_id": proxy_id,
            "date": self._today_date,
            "total_requests": total,
            "success_requests": success,
            "failed_requests": stats.get("failed_requests", 0),
            "success_rate": success / total if total > 0 else 0,
            "avg_response_time": (
                stats.get("total_response_time", 0) / success if success > 0 else 0
            ),
            "total_bytes_sent": stats.get("total_bytes_sent", 0),
            "total_bytes_received": stats.get("total_bytes_received", 0),
            "unique_accounts": len(stats.get("accounts", set())),
            "platforms_used": list(stats.get("platforms", set())),
        }
    
    def get_all_realtime_stats(self) -> List[Dict]:
        """获取所有代理的实时统计"""
        return [
            self.get_realtime_stats(proxy_id)
            for proxy_id in self._today_stats.keys()
        ]
    
    async def aggregate_daily_stats(self) -> None:
        """聚合今日统计并保存"""
        for proxy_id, stats in self._today_stats.items():
            total = stats["total_requests"]
            success = stats["success_requests"]
            
            daily = ProxyDailyStats(
                proxy_id=proxy_id,
                stat_date=self._today_date,
                total_requests=total,
                success_requests=success,
                failed_requests=stats["failed_requests"],
                total_bytes_sent=stats["total_bytes_sent"],
                total_bytes_received=stats["total_bytes_received"],
                avg_response_time=(
                    stats["total_response_time"] / success if success > 0 else 0
                ),
                unique_accounts=len(stats["accounts"]),
                platforms_used=list(stats["platforms"]),
            )
            
            try:
                await self._store.save_daily_stats(daily)
            except Exception as e:
                utils.logger.error(
                    f"[StatisticsCollector] Failed to save daily stats for {proxy_id}: {e}"
                )

