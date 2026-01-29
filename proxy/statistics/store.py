# -*- coding: utf-8 -*-
# @Desc    : 统计数据存储

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite

from ..types import ProxyUsageRecord, ProxyDailyStats


class StatisticsStore(ABC):
    """统计存储抽象基类"""
    
    @abstractmethod
    async def init(self) -> None:
        """初始化存储"""
        raise NotImplementedError
    
    @abstractmethod
    async def close(self) -> None:
        """关闭存储"""
        raise NotImplementedError
    
    @abstractmethod
    async def save_usage_record(self, record: ProxyUsageRecord) -> None:
        """保存使用记录"""
        raise NotImplementedError
    
    @abstractmethod
    async def save_usage_records(self, records: List[ProxyUsageRecord]) -> int:
        """批量保存使用记录"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_usage_records(
        self,
        proxy_id: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ProxyUsageRecord]:
        """获取使用记录"""
        raise NotImplementedError
    
    @abstractmethod
    async def save_daily_stats(self, stats: ProxyDailyStats) -> None:
        """保存每日统计"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_daily_stats(
        self,
        proxy_id: str,
        date: str,
    ) -> Optional[ProxyDailyStats]:
        """获取每日统计"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_daily_stats_range(
        self,
        proxy_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ProxyDailyStats]:
        """获取日期范围内的统计"""
        raise NotImplementedError
    
    @abstractmethod
    async def cleanup_old_records(self, retention_days: int = 30) -> int:
        """清理旧记录"""
        raise NotImplementedError


class SQLiteStatisticsStore(StatisticsStore):
    """SQLite统计存储实现"""
    
    def __init__(self, db_path: str = "data/proxy_stats.db"):
        self.db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def init(self) -> None:
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS proxy_usage_logs (
                record_id TEXT PRIMARY KEY,
                proxy_id TEXT NOT NULL,
                account_id TEXT,
                platform TEXT NOT NULL,
                request_url TEXT,
                request_method TEXT DEFAULT 'GET',
                response_code INTEGER,
                response_time_ms REAL DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0,
                bytes_received INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                error_type TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS proxy_daily_stats (
                proxy_id TEXT NOT NULL,
                stat_date TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                success_requests INTEGER DEFAULT 0,
                failed_requests INTEGER DEFAULT 0,
                total_bytes_sent INTEGER DEFAULT 0,
                total_bytes_received INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                unique_accounts INTEGER DEFAULT 0,
                platforms_used TEXT,
                updated_at TEXT,
                PRIMARY KEY (proxy_id, stat_date)
            );
            
            CREATE TABLE IF NOT EXISTS platform_daily_stats (
                platform TEXT NOT NULL,
                stat_date TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                success_requests INTEGER DEFAULT 0,
                failed_requests INTEGER DEFAULT 0,
                unique_proxies INTEGER DEFAULT 0,
                unique_accounts INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                updated_at TEXT,
                PRIMARY KEY (platform, stat_date)
            );
            
            CREATE INDEX IF NOT EXISTS idx_usage_logs_proxy ON proxy_usage_logs(proxy_id);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_platform ON proxy_usage_logs(platform);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_time ON proxy_usage_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON proxy_daily_stats(stat_date);
        """)
        await self._conn.commit()
    
    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def save_usage_record(self, record: ProxyUsageRecord) -> None:
        """保存使用记录"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        await self._conn.execute("""
            INSERT OR REPLACE INTO proxy_usage_logs (
                record_id, proxy_id, account_id, platform,
                request_url, request_method, response_code, response_time_ms,
                bytes_sent, bytes_received, success, error_type, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.record_id, record.proxy_id, record.account_id, record.platform,
            record.request_url, record.request_method, record.response_code, record.response_time_ms,
            record.bytes_sent, record.bytes_received, 1 if record.success else 0,
            record.error_type, record.error_message, record.created_at.isoformat(),
        ))
        await self._conn.commit()
    
    async def save_usage_records(self, records: List[ProxyUsageRecord]) -> int:
        """批量保存使用记录"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        count = 0
        for record in records:
            try:
                await self.save_usage_record(record)
                count += 1
            except Exception:
                continue
        return count
    
    async def get_usage_records(
        self,
        proxy_id: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ProxyUsageRecord]:
        """获取使用记录"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        query = "SELECT * FROM proxy_usage_logs WHERE 1=1"
        params: List = []
        
        if proxy_id:
            query += " AND proxy_id = ?"
            params.append(proxy_id)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if start_time:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())
        if end_time:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        records = []
        async with self._conn.execute(query, params) as cursor:
            async for row in cursor:
                records.append(ProxyUsageRecord(
                    record_id=row["record_id"],
                    proxy_id=row["proxy_id"],
                    account_id=row["account_id"],
                    platform=row["platform"],
                    request_url=row["request_url"],
                    request_method=row["request_method"],
                    response_code=row["response_code"],
                    response_time_ms=row["response_time_ms"],
                    bytes_sent=row["bytes_sent"],
                    bytes_received=row["bytes_received"],
                    success=bool(row["success"]),
                    error_type=row["error_type"],
                    error_message=row["error_message"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                ))
        return records
    
    async def save_daily_stats(self, stats: ProxyDailyStats) -> None:
        """保存每日统计"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        await self._conn.execute("""
            INSERT OR REPLACE INTO proxy_daily_stats (
                proxy_id, stat_date, total_requests, success_requests, failed_requests,
                total_bytes_sent, total_bytes_received, avg_response_time,
                unique_accounts, platforms_used, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stats.proxy_id, stats.stat_date, stats.total_requests,
            stats.success_requests, stats.failed_requests,
            stats.total_bytes_sent, stats.total_bytes_received, stats.avg_response_time,
            stats.unique_accounts, json.dumps(stats.platforms_used),
            datetime.now().isoformat(),
        ))
        await self._conn.commit()
    
    async def get_daily_stats(
        self,
        proxy_id: str,
        date: str,
    ) -> Optional[ProxyDailyStats]:
        """获取每日统计"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        async with self._conn.execute(
            "SELECT * FROM proxy_daily_stats WHERE proxy_id = ? AND stat_date = ?",
            (proxy_id, date)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return ProxyDailyStats(
                    proxy_id=row["proxy_id"],
                    stat_date=row["stat_date"],
                    total_requests=row["total_requests"],
                    success_requests=row["success_requests"],
                    failed_requests=row["failed_requests"],
                    total_bytes_sent=row["total_bytes_sent"],
                    total_bytes_received=row["total_bytes_received"],
                    avg_response_time=row["avg_response_time"],
                    unique_accounts=row["unique_accounts"],
                    platforms_used=json.loads(row["platforms_used"]) if row["platforms_used"] else [],
                )
        return None
    
    async def get_daily_stats_range(
        self,
        proxy_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ProxyDailyStats]:
        """获取日期范围内的统计"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        query = "SELECT * FROM proxy_daily_stats WHERE 1=1"
        params: List = []
        
        if proxy_id:
            query += " AND proxy_id = ?"
            params.append(proxy_id)
        if start_date:
            query += " AND stat_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND stat_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY stat_date DESC"
        
        stats_list = []
        async with self._conn.execute(query, params) as cursor:
            async for row in cursor:
                stats_list.append(ProxyDailyStats(
                    proxy_id=row["proxy_id"],
                    stat_date=row["stat_date"],
                    total_requests=row["total_requests"],
                    success_requests=row["success_requests"],
                    failed_requests=row["failed_requests"],
                    total_bytes_sent=row["total_bytes_sent"],
                    total_bytes_received=row["total_bytes_received"],
                    avg_response_time=row["avg_response_time"],
                    unique_accounts=row["unique_accounts"],
                    platforms_used=json.loads(row["platforms_used"]) if row["platforms_used"] else [],
                ))
        return stats_list
    
    async def cleanup_old_records(self, retention_days: int = 30) -> int:
        """清理旧记录"""
        if not self._conn:
            raise RuntimeError("Database not initialized")
        
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        cursor = await self._conn.execute(
            "DELETE FROM proxy_usage_logs WHERE created_at < ?", (cutoff_date,)
        )
        deleted = cursor.rowcount
        
        await self._conn.commit()
        return deleted

