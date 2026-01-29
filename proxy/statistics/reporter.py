# -*- coding: utf-8 -*-
# @Desc    : 代理统计报表生成器

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tools.utils import utils

from .store import StatisticsStore


class ProxyStatisticsReporter:
    """
    代理统计报表生成器
    
    功能:
    - 生成各种维度的统计报表
    - 支持按代理、平台、时间等聚合
    """
    
    def __init__(self, store: StatisticsStore):
        """
        初始化报表生成器
        
        Args:
            store: 统计存储
        """
        self._store = store
    
    async def get_proxy_summary(
        self,
        proxy_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取代理汇总报表
        
        Args:
            proxy_id: 代理ID
            days: 统计天数
            
        Returns:
            汇总报表
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        
        # 获取每日统计
        daily_stats = await self._store.get_daily_stats_range(
            proxy_id=proxy_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        if not daily_stats:
            return {
                "proxy_id": proxy_id,
                "period": f"{start_date} ~ {end_date}",
                "total_requests": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "total_traffic": 0,
                "daily_data": [],
            }
        
        # 聚合统计
        total_requests = sum(s.total_requests for s in daily_stats)
        success_requests = sum(s.success_requests for s in daily_stats)
        total_response_time = sum(s.avg_response_time * s.success_requests for s in daily_stats)
        total_bytes = sum(s.total_bytes_sent + s.total_bytes_received for s in daily_stats)
        all_platforms = set()
        
        for s in daily_stats:
            all_platforms.update(s.platforms_used)
        
        return {
            "proxy_id": proxy_id,
            "period": f"{start_date} ~ {end_date}",
            "total_requests": total_requests,
            "success_requests": success_requests,
            "failed_requests": sum(s.failed_requests for s in daily_stats),
            "success_rate": success_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": total_response_time / success_requests if success_requests > 0 else 0,
            "total_traffic_bytes": total_bytes,
            "total_traffic_mb": total_bytes / (1024 * 1024),
            "platforms_used": list(all_platforms),
            "daily_data": [
                {
                    "date": s.stat_date,
                    "total_requests": s.total_requests,
                    "success_rate": s.success_requests / s.total_requests if s.total_requests > 0 else 0,
                    "avg_response_time": s.avg_response_time,
                }
                for s in daily_stats
            ],
        }
    
    async def get_overview_report(
        self,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取总览报表
        
        Args:
            days: 统计天数
            
        Returns:
            总览报表
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        
        # 获取所有代理的统计
        all_stats = await self._store.get_daily_stats_range(
            start_date=start_date,
            end_date=end_date,
        )
        
        if not all_stats:
            return {
                "period": f"{start_date} ~ {end_date}",
                "total_proxies": 0,
                "total_requests": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "total_traffic_mb": 0,
                "daily_trend": [],
                "top_proxies": [],
            }
        
        # 聚合统计
        proxy_ids = set()
        total_requests = 0
        success_requests = 0
        total_response_time = 0
        total_bytes = 0
        
        # 按日期聚合
        daily_aggregated: Dict[str, Dict] = {}
        # 按代理聚合
        proxy_aggregated: Dict[str, Dict] = {}
        
        for s in all_stats:
            proxy_ids.add(s.proxy_id)
            total_requests += s.total_requests
            success_requests += s.success_requests
            total_response_time += s.avg_response_time * s.success_requests
            total_bytes += s.total_bytes_sent + s.total_bytes_received
            
            # 按日期聚合
            if s.stat_date not in daily_aggregated:
                daily_aggregated[s.stat_date] = {
                    "total": 0,
                    "success": 0,
                    "response_time_sum": 0,
                }
            daily_aggregated[s.stat_date]["total"] += s.total_requests
            daily_aggregated[s.stat_date]["success"] += s.success_requests
            daily_aggregated[s.stat_date]["response_time_sum"] += s.avg_response_time * s.success_requests
            
            # 按代理聚合
            if s.proxy_id not in proxy_aggregated:
                proxy_aggregated[s.proxy_id] = {
                    "total": 0,
                    "success": 0,
                    "response_time_sum": 0,
                }
            proxy_aggregated[s.proxy_id]["total"] += s.total_requests
            proxy_aggregated[s.proxy_id]["success"] += s.success_requests
            proxy_aggregated[s.proxy_id]["response_time_sum"] += s.avg_response_time * s.success_requests
        
        # 生成每日趋势
        daily_trend = []
        for date in sorted(daily_aggregated.keys()):
            d = daily_aggregated[date]
            daily_trend.append({
                "date": date,
                "total_requests": d["total"],
                "success_rate": d["success"] / d["total"] if d["total"] > 0 else 0,
                "avg_response_time": d["response_time_sum"] / d["success"] if d["success"] > 0 else 0,
            })
        
        # 生成Top代理
        top_proxies = []
        for proxy_id in sorted(
            proxy_aggregated.keys(),
            key=lambda p: proxy_aggregated[p]["total"],
            reverse=True
        )[:10]:
            p = proxy_aggregated[proxy_id]
            top_proxies.append({
                "proxy_id": proxy_id,
                "total_requests": p["total"],
                "success_rate": p["success"] / p["total"] if p["total"] > 0 else 0,
                "avg_response_time": p["response_time_sum"] / p["success"] if p["success"] > 0 else 0,
            })
        
        return {
            "period": f"{start_date} ~ {end_date}",
            "total_proxies": len(proxy_ids),
            "total_requests": total_requests,
            "success_requests": success_requests,
            "failed_requests": total_requests - success_requests,
            "success_rate": success_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": total_response_time / success_requests if success_requests > 0 else 0,
            "total_traffic_bytes": total_bytes,
            "total_traffic_mb": total_bytes / (1024 * 1024),
            "daily_trend": daily_trend,
            "top_proxies": top_proxies,
        }
    
    async def get_platform_report(
        self,
        platform: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取平台报表
        
        Args:
            platform: 平台名称
            days: 统计天数
            
        Returns:
            平台报表
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 获取该平台的使用记录
        records = await self._store.get_usage_records(
            platform=platform,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )
        
        if not records:
            return {
                "platform": platform,
                "period": f"{start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}",
                "total_requests": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "unique_proxies": 0,
                "unique_accounts": 0,
            }
        
        # 聚合统计
        total_requests = len(records)
        success_requests = sum(1 for r in records if r.success)
        total_response_time = sum(r.response_time_ms for r in records if r.success)
        proxy_ids = set(r.proxy_id for r in records)
        account_ids = set(r.account_id for r in records if r.account_id)
        
        return {
            "platform": platform,
            "period": f"{start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}",
            "total_requests": total_requests,
            "success_requests": success_requests,
            "failed_requests": total_requests - success_requests,
            "success_rate": success_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": total_response_time / success_requests if success_requests > 0 else 0,
            "unique_proxies": len(proxy_ids),
            "unique_accounts": len(account_ids),
        }
    
    async def get_usage_history(
        self,
        proxy_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        获取使用历史
        
        Args:
            proxy_id: 代理ID
            platform: 平台
            limit: 返回数量
            
        Returns:
            使用记录列表
        """
        records = await self._store.get_usage_records(
            proxy_id=proxy_id,
            platform=platform,
            limit=limit,
        )
        
        return [
            {
                "record_id": r.record_id,
                "proxy_id": r.proxy_id,
                "account_id": r.account_id,
                "platform": r.platform,
                "request_url": r.request_url,
                "request_method": r.request_method,
                "response_code": r.response_code,
                "response_time_ms": r.response_time_ms,
                "success": r.success,
                "error_type": r.error_type,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]

