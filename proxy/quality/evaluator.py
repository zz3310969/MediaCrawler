# -*- coding: utf-8 -*-
# @Desc    : 代理质量评估器

import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional

from tools.utils import utils

from ..persistence.proxy_store import ProxyStore
from ..types import ProxyQualityMetrics


@dataclass
class ResponseTimeSample:
    """响应时间样本"""
    timestamp: float
    response_time_ms: float
    success: bool


class ProxyQualityEvaluator:
    """
    代理质量评估器
    
    功能:
    - 记录请求成功/失败
    - 计算质量指标（成功率、响应时间、稳定性）
    - 计算综合质量分
    - 支持时间窗口统计
    """
    
    # 质量分权重配置
    WEIGHT_SUCCESS_RATE = 60       # 成功率权重 (0-60)
    WEIGHT_RESPONSE_TIME = 30      # 响应时间权重 (0-30)
    WEIGHT_STABILITY = 10          # 稳定性权重 (0-10)
    
    # 响应时间阈值 (毫秒)
    RESPONSE_TIME_EXCELLENT = 500   # 优秀
    RESPONSE_TIME_GOOD = 1000       # 良好
    RESPONSE_TIME_POOR = 3000       # 较差
    RESPONSE_TIME_BAD = 5000        # 很差
    
    # 采样窗口配置
    DEFAULT_SAMPLE_WINDOW = 100     # 保留最近100个样本
    DEFAULT_TIME_WINDOW_HOURS = 24  # 24小时时间窗口
    
    def __init__(
        self,
        proxy_store: ProxyStore,
        sample_window: int = DEFAULT_SAMPLE_WINDOW,
        time_window_hours: int = DEFAULT_TIME_WINDOW_HOURS,
    ):
        """
        初始化评估器
        
        Args:
            proxy_store: 代理存储
            sample_window: 样本窗口大小
            time_window_hours: 时间窗口（小时）
        """
        self._proxy_store = proxy_store
        self._sample_window = sample_window
        self._time_window_hours = time_window_hours
        
        # 内存中的响应时间样本缓存
        self._samples: Dict[str, Deque[ResponseTimeSample]] = {}
        
        # 内存中的质量指标缓存
        self._metrics_cache: Dict[str, ProxyQualityMetrics] = {}
    
    def _get_samples(self, proxy_id: str) -> Deque[ResponseTimeSample]:
        """获取代理的样本队列"""
        if proxy_id not in self._samples:
            self._samples[proxy_id] = deque(maxlen=self._sample_window)
        return self._samples[proxy_id]
    
    async def _get_or_create_metrics(self, proxy_id: str) -> ProxyQualityMetrics:
        """获取或创建质量指标"""
        if proxy_id in self._metrics_cache:
            return self._metrics_cache[proxy_id]
        
        # 从存储加载
        metrics = await self._proxy_store.get_quality_metrics(proxy_id)
        if not metrics:
            metrics = ProxyQualityMetrics(proxy_id=proxy_id)
        
        self._metrics_cache[proxy_id] = metrics
        return metrics
    
    async def record_success(
        self,
        proxy_id: str,
        response_time_ms: float,
    ) -> ProxyQualityMetrics:
        """
        记录成功请求
        
        Args:
            proxy_id: 代理ID
            response_time_ms: 响应时间（毫秒）
            
        Returns:
            更新后的质量指标
        """
        # 添加样本
        samples = self._get_samples(proxy_id)
        samples.append(ResponseTimeSample(
            timestamp=time.time(),
            response_time_ms=response_time_ms,
            success=True,
        ))
        
        # 更新指标
        metrics = await self._get_or_create_metrics(proxy_id)
        metrics.record_success(response_time_ms)
        
        # 更新P95
        metrics.p95_response_time = self._calculate_p95(samples)
        
        # 保存到存储
        await self._proxy_store.save_quality_metrics(metrics)
        
        utils.logger.debug(
            f"[QualityEvaluator] Proxy {proxy_id} success: "
            f"{response_time_ms:.0f}ms, score={metrics.quality_score:.1f}"
        )
        
        return metrics
    
    async def record_failure(
        self,
        proxy_id: str,
        is_timeout: bool = False,
        error_type: Optional[str] = None,
    ) -> ProxyQualityMetrics:
        """
        记录失败请求
        
        Args:
            proxy_id: 代理ID
            is_timeout: 是否超时
            error_type: 错误类型
            
        Returns:
            更新后的质量指标
        """
        # 添加样本
        samples = self._get_samples(proxy_id)
        samples.append(ResponseTimeSample(
            timestamp=time.time(),
            response_time_ms=0,
            success=False,
        ))
        
        # 更新指标
        metrics = await self._get_or_create_metrics(proxy_id)
        metrics.record_failure(is_timeout)
        
        # 保存到存储
        await self._proxy_store.save_quality_metrics(metrics)
        
        utils.logger.warning(
            f"[QualityEvaluator] Proxy {proxy_id} failed: "
            f"timeout={is_timeout}, consecutive_failures={metrics.consecutive_failures}, "
            f"score={metrics.quality_score:.1f}"
        )
        
        return metrics
    
    def _calculate_p95(self, samples: Deque[ResponseTimeSample]) -> float:
        """计算P95响应时间"""
        success_times = [s.response_time_ms for s in samples if s.success]
        if not success_times:
            return 0.0
        
        sorted_times = sorted(success_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[min(p95_index, len(sorted_times) - 1)]
    
    async def get_quality_score(self, proxy_id: str) -> float:
        """
        获取代理质量分
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            质量分 (0-100)
        """
        metrics = await self._get_or_create_metrics(proxy_id)
        return metrics.quality_score
    
    async def get_metrics(self, proxy_id: str) -> ProxyQualityMetrics:
        """获取代理质量指标"""
        return await self._get_or_create_metrics(proxy_id)
    
    async def get_recent_success_rate(
        self,
        proxy_id: str,
        recent_count: int = 10,
    ) -> float:
        """
        获取最近N次请求的成功率
        
        Args:
            proxy_id: 代理ID
            recent_count: 最近的请求数
            
        Returns:
            成功率 (0-1)
        """
        samples = self._get_samples(proxy_id)
        if not samples:
            return 0.0
        
        recent = list(samples)[-recent_count:]
        if not recent:
            return 0.0
        
        success_count = sum(1 for s in recent if s.success)
        return success_count / len(recent)
    
    async def get_time_window_stats(
        self,
        proxy_id: str,
        hours: Optional[int] = None,
    ) -> Dict:
        """
        获取时间窗口内的统计信息
        
        Args:
            proxy_id: 代理ID
            hours: 时间窗口（小时），默认使用配置值
            
        Returns:
            统计信息字典
        """
        hours = hours or self._time_window_hours
        cutoff_time = time.time() - hours * 3600
        
        samples = self._get_samples(proxy_id)
        recent_samples = [s for s in samples if s.timestamp >= cutoff_time]
        
        if not recent_samples:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "p95_response_time": 0.0,
            }
        
        success_samples = [s for s in recent_samples if s.success]
        success_times = [s.response_time_ms for s in success_samples]
        
        return {
            "total_requests": len(recent_samples),
            "success_rate": len(success_samples) / len(recent_samples),
            "avg_response_time": statistics.mean(success_times) if success_times else 0.0,
            "p95_response_time": self._calculate_percentile(success_times, 95) if success_times else 0.0,
        }
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    async def is_proxy_healthy(
        self,
        proxy_id: str,
        min_success_rate: float = 0.5,
        max_consecutive_failures: int = 5,
    ) -> bool:
        """
        检查代理是否健康
        
        Args:
            proxy_id: 代理ID
            min_success_rate: 最低成功率要求
            max_consecutive_failures: 最大连续失败次数
            
        Returns:
            是否健康
        """
        metrics = await self._get_or_create_metrics(proxy_id)
        
        # 检查连续失败
        if metrics.consecutive_failures >= max_consecutive_failures:
            return False
        
        # 检查成功率（至少有一定请求量时）
        if metrics.total_requests >= 10 and metrics.success_rate < min_success_rate:
            return False
        
        return True
    
    async def should_retire(
        self,
        proxy_id: str,
        min_score: float = 30,
        min_requests: int = 20,
    ) -> bool:
        """
        判断代理是否应该被淘汰
        
        Args:
            proxy_id: 代理ID
            min_score: 最低质量分
            min_requests: 最小请求数（低于此值不淘汰）
            
        Returns:
            是否应该淘汰
        """
        metrics = await self._get_or_create_metrics(proxy_id)
        
        # 请求数不足，不淘汰
        if metrics.total_requests < min_requests:
            return False
        
        return metrics.quality_score < min_score
    
    async def get_all_metrics(self) -> List[ProxyQualityMetrics]:
        """获取所有缓存的质量指标"""
        return list(self._metrics_cache.values())
    
    def clear_cache(self, proxy_id: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            proxy_id: 代理ID，为空则清除所有
        """
        if proxy_id:
            self._samples.pop(proxy_id, None)
            self._metrics_cache.pop(proxy_id, None)
        else:
            self._samples.clear()
            self._metrics_cache.clear()
    
    async def refresh_from_store(self, proxy_id: str) -> ProxyQualityMetrics:
        """从存储刷新质量指标"""
        self._metrics_cache.pop(proxy_id, None)
        return await self._get_or_create_metrics(proxy_id)

