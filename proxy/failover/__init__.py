# -*- coding: utf-8 -*-
# @Desc    : 代理故障转移模块

from .strategy import (
    FailoverStrategy,
    SimpleFailoverStrategy,
    StickyFailoverStrategy,
    WeightedFailoverStrategy,
    CircuitBreakerStrategy,
)
from .manager import ProxyFailoverManager

__all__ = [
    "FailoverStrategy",
    "SimpleFailoverStrategy",
    "StickyFailoverStrategy",
    "WeightedFailoverStrategy",
    "CircuitBreakerStrategy",
    "ProxyFailoverManager",
]

