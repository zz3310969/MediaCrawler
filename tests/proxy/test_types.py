# -*- coding: utf-8 -*-
# @Desc    : 代理类型测试

import pytest
import time

from proxy.types import (
    IpInfoModel,
    ProxyProtocol,
    ProxySource,
    ProxyStatus,
    ProxyQualityMetrics,
    ProxyRegionInfo,
    AccountProxyBinding,
    BindingStatus,
    PersistedProxy,
)


class TestProxyProtocol:
    """ProxyProtocol 测试"""
    
    def test_from_string(self):
        """测试字符串解析"""
        assert ProxyProtocol.from_string("http") == ProxyProtocol.HTTP
        assert ProxyProtocol.from_string("HTTP") == ProxyProtocol.HTTP
        assert ProxyProtocol.from_string("http://") == ProxyProtocol.HTTP
        assert ProxyProtocol.from_string("socks5") == ProxyProtocol.SOCKS5
        assert ProxyProtocol.from_string("unknown") == ProxyProtocol.HTTP  # 默认
    
    def test_values(self):
        """测试枚举值"""
        assert ProxyProtocol.HTTP.value == "http"
        assert ProxyProtocol.HTTPS.value == "https"
        assert ProxyProtocol.SOCKS5.value == "socks5"


class TestIpInfoModel:
    """IpInfoModel 测试"""
    
    def test_basic_creation(self):
        """测试基本创建"""
        proxy = IpInfoModel(ip="192.168.1.1", port=8080)
        assert proxy.ip == "192.168.1.1"
        assert proxy.port == 8080
        assert proxy.protocol == "http"  # 默认
        assert proxy.proxy_id is not None
    
    def test_with_auth(self):
        """测试带认证"""
        proxy = IpInfoModel(
            ip="192.168.1.1",
            port=8080,
            user="admin",
            password="secret",
        )
        assert proxy.user == "admin"
        assert proxy.password == "secret"
    
    def test_protocol_normalization(self):
        """测试协议标准化"""
        proxy = IpInfoModel(ip="192.168.1.1", port=8080, protocol="HTTPS://")
        assert proxy.protocol == "https"
    
    def test_to_url(self):
        """测试URL转换"""
        proxy = IpInfoModel(ip="192.168.1.1", port=8080)
        assert proxy.to_url() == "http://192.168.1.1:8080"
        
        proxy_auth = IpInfoModel(
            ip="192.168.1.1", port=8080, user="admin", password="secret"
        )
        assert proxy_auth.to_url() == "http://admin:secret@192.168.1.1:8080"
    
    def test_to_playwright_proxy(self):
        """测试Playwright格式"""
        proxy = IpInfoModel(ip="192.168.1.1", port=8080)
        result = proxy.to_playwright_proxy()
        assert result["server"] == "http://192.168.1.1:8080"
        
        proxy_auth = IpInfoModel(
            ip="192.168.1.1", port=8080, user="admin", password="secret"
        )
        result = proxy_auth.to_playwright_proxy()
        assert result["username"] == "admin"
        assert result["password"] == "secret"
    
    def test_is_expired(self):
        """测试过期检查"""
        # 未设置过期时间
        proxy = IpInfoModel(ip="192.168.1.1", port=8080)
        assert proxy.is_expired() is False
        
        # 已过期
        proxy_expired = IpInfoModel(
            ip="192.168.1.1", port=8080,
            expired_time_ts=int(time.time()) - 100,
        )
        assert proxy_expired.is_expired() is True
        
        # 未过期
        proxy_valid = IpInfoModel(
            ip="192.168.1.1", port=8080,
            expired_time_ts=int(time.time()) + 3600,
        )
        assert proxy_valid.is_expired() is False
    
    def test_is_expired_with_buffer(self):
        """测试带缓冲的过期检查"""
        # 50秒后过期，但缓冲60秒，所以认为已过期
        proxy = IpInfoModel(
            ip="192.168.1.1", port=8080,
            expired_time_ts=int(time.time()) + 50,
        )
        assert proxy.is_expired(buffer_seconds=60) is True
        assert proxy.is_expired(buffer_seconds=30) is False
    
    def test_is_socks(self):
        """测试SOCKS判断"""
        proxy_http = IpInfoModel(ip="192.168.1.1", port=8080)
        assert proxy_http.is_socks() is False
        
        proxy_socks5 = IpInfoModel(ip="192.168.1.1", port=1080, protocol="socks5")
        assert proxy_socks5.is_socks() is True
    
    def test_proxy_id_generation(self):
        """测试ID生成"""
        proxy1 = IpInfoModel(ip="192.168.1.1", port=8080)
        proxy2 = IpInfoModel(ip="192.168.1.1", port=8080)
        proxy3 = IpInfoModel(ip="192.168.1.2", port=8080)
        
        assert proxy1.proxy_id == proxy2.proxy_id  # 相同IP:端口生成相同ID
        assert proxy1.proxy_id != proxy3.proxy_id  # 不同IP生成不同ID


class TestProxyQualityMetrics:
    """ProxyQualityMetrics 测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        assert metrics.total_requests == 0
        assert metrics.success_rate == 0.0
        assert metrics.quality_score == 0.0  # 无请求时为0
    
    def test_record_success(self):
        """测试记录成功"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        metrics.record_success(100.0)
        
        assert metrics.total_requests == 1
        assert metrics.success_requests == 1
        assert metrics.avg_response_time == 100.0
        assert metrics.consecutive_successes == 1
        assert metrics.consecutive_failures == 0
    
    def test_record_failure(self):
        """测试记录失败"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        metrics.record_failure()
        
        assert metrics.total_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.consecutive_failures == 1
        assert metrics.consecutive_successes == 0
    
    def test_success_rate(self):
        """测试成功率计算"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        metrics.record_success(100.0)
        metrics.record_success(100.0)
        metrics.record_failure()
        
        assert metrics.success_rate == pytest.approx(2/3)
    
    def test_quality_score(self):
        """测试质量分计算"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        
        # 记录一些成功请求
        for _ in range(10):
            metrics.record_success(500.0)  # 500ms响应时间
        
        # 质量分应该比较高
        assert metrics.quality_score > 50
    
    def test_consecutive_reset(self):
        """测试连续计数重置"""
        metrics = ProxyQualityMetrics(proxy_id="test")
        
        metrics.record_success(100.0)
        metrics.record_success(100.0)
        assert metrics.consecutive_successes == 2
        
        metrics.record_failure()
        assert metrics.consecutive_successes == 0
        assert metrics.consecutive_failures == 1
        
        metrics.record_success(100.0)
        assert metrics.consecutive_failures == 0
        assert metrics.consecutive_successes == 1


class TestProxyRegionInfo:
    """ProxyRegionInfo 测试"""
    
    def test_similarity_same_region(self):
        """测试相同地区相似度"""
        region1 = ProxyRegionInfo(
            proxy_id="1",
            country="CN",
            province="北京",
            city="北京",
            isp="电信",
        )
        region2 = ProxyRegionInfo(
            proxy_id="2",
            country="CN",
            province="北京",
            city="北京",
            isp="电信",
        )
        
        assert region1.similarity_score(region2) == 1.0
    
    def test_similarity_different_region(self):
        """测试不同地区相似度"""
        region1 = ProxyRegionInfo(
            proxy_id="1",
            country="CN",
            province="北京",
            city="北京",
            isp="电信",
        )
        region2 = ProxyRegionInfo(
            proxy_id="2",
            country="US",
            province="California",
            city="Los Angeles",
            isp="AT&T",
        )
        
        assert region1.similarity_score(region2) == 0.0
    
    def test_similarity_partial(self):
        """测试部分匹配"""
        region1 = ProxyRegionInfo(
            proxy_id="1",
            country="CN",
            province="北京",
            city="北京",
            isp="电信",
        )
        region2 = ProxyRegionInfo(
            proxy_id="2",
            country="CN",
            province="上海",
            city="上海",
            isp="电信",
        )
        
        # 国家和ISP相同
        score = region1.similarity_score(region2)
        assert 0 < score < 1


class TestPersistedProxy:
    """PersistedProxy 测试"""
    
    def test_to_ip_info_model(self):
        """测试转换为IpInfoModel"""
        persisted = PersistedProxy(
            proxy_id="test",
            ip="192.168.1.1",
            port=8080,
            protocol="http",
            username="admin",
            password="secret",
            source="manual",
        )
        
        ip_info = persisted.to_ip_info_model()
        assert ip_info.ip == "192.168.1.1"
        assert ip_info.port == 8080
        assert ip_info.user == "admin"
        assert ip_info.password == "secret"
    
    def test_from_ip_info_model(self):
        """测试从IpInfoModel创建"""
        ip_info = IpInfoModel(
            ip="192.168.1.1",
            port=8080,
            user="admin",
            password="secret",
        )
        
        persisted = PersistedProxy.from_ip_info_model(ip_info, source="manual")
        assert persisted.ip == "192.168.1.1"
        assert persisted.port == 8080
        assert persisted.username == "admin"
        assert persisted.source == "manual"

