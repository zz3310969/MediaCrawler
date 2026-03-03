# -*- coding: utf-8 -*-
# WebUI 相关数据库模型
# 包含用户管理、任务管理、账号管理、代理管理等

from sqlalchemy import Column, Integer, String, Text, BigInteger, Float, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """WebUI登录用户表"""
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True, comment='用户唯一ID')
    username = Column(String(128), nullable=False, unique=True, index=True, comment='登录用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    email = Column(String(255), default='', comment='邮箱')
    nickname = Column(String(128), default='', comment='显示昵称')
    avatar = Column(Text, default='', comment='头像URL')
    role = Column(String(32), default='user', comment='角色: admin/user')
    status = Column(String(32), default='active', comment='状态: active/inactive/banned')
    last_login_at = Column(BigInteger, default=0, comment='最后登录时间戳')
    last_login_ip = Column(String(64), default='', comment='最后登录IP')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳')
    updated_at = Column(BigInteger, nullable=False, comment='更新时间戳')
    
    __table_args__ = (
        Index('idx_user_status', 'status'),
    )


class CrawlerTask(Base):
    """爬虫任务表"""
    __tablename__ = 'crawler_task'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), nullable=False, unique=True, index=True, comment='任务唯一ID')
    user_id = Column(String(64), default='', index=True, comment='创建者用户ID')
    session_id = Column(String(64), default='', index=True, comment='会话ID')
    task_name = Column(String(255), default='', comment='任务名称')
    platform = Column(String(32), nullable=False, index=True, comment='平台: xhs/dy/bili/wb/wechat/ks/tieba/zhihu')
    crawler_type = Column(String(32), default='search', comment='爬取类型: search/creator/detail/creator_vip/album')
    status = Column(String(32), default='pending', index=True, comment='状态: pending/running/completed/failed/cancelled')
    priority = Column(Integer, default=5, comment='优先级 1-10')
    config = Column(Text, default='{}', comment='任务配置JSON')
    progress = Column(Text, default='{}', comment='进度信息JSON')
    result = Column(Text, default='{}', comment='执行结果JSON')
    task_metadata = Column(Text, default='{}', comment='元数据JSON')
    retry_count = Column(Integer, default=0, comment='重试次数')
    max_retries = Column(Integer, default=3, comment='最大重试次数')
    error_message = Column(Text, default='', comment='错误信息')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳')
    scheduled_at = Column(BigInteger, default=0, comment='计划执行时间戳')
    started_at = Column(BigInteger, default=0, comment='开始时间戳')
    finished_at = Column(BigInteger, default=0, comment='完成时间戳')
    last_heartbeat_at = Column(BigInteger, default=0, comment='最后心跳时间戳')
    
    __table_args__ = (
        Index('idx_task_status_platform', 'status', 'platform'),
        Index('idx_task_created', 'created_at'),
    )


class TaskLog(Base):
    """任务日志表"""
    __tablename__ = 'task_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(64), nullable=False, unique=True, index=True, comment='日志唯一ID')
    task_id = Column(String(64), nullable=False, index=True, comment='关联任务ID')
    level = Column(String(16), default='info', index=True, comment='日志级别: debug/info/warn/error')
    message = Column(Text, default='', comment='日志内容')
    extra = Column(Text, default='{}', comment='扩展信息JSON')
    created_at = Column(BigInteger, nullable=False, index=True, comment='创建时间戳')


class CrawlerAccount(Base):
    """爬虫账号表 - 管理各平台的登录账号"""
    __tablename__ = 'crawler_account'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(64), nullable=False, unique=True, index=True, comment='账号唯一ID')
    platform = Column(String(32), nullable=False, index=True, comment='平台标识')
    username = Column(String(255), default='', comment='用户名/账号')
    nickname = Column(String(255), default='', comment='昵称')
    avatar = Column(Text, default='', comment='头像URL')
    status = Column(String(32), default='pending', index=True, comment='状态: active/inactive/pending/expired')
    login_method = Column(String(32), default='cookie', comment='登录方式: qrcode/cookie/phone')
    cookies = Column(Text, default='', comment='Cookie数据')
    cookie_valid = Column(Integer, default=0, comment='Cookie是否有效 0/1')
    last_used_at = Column(BigInteger, default=0, comment='最后使用时间戳')
    last_validated_at = Column(BigInteger, default=0, comment='最后验证时间戳')
    expires_at = Column(BigInteger, default=0, comment='过期时间戳')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳')
    updated_at = Column(BigInteger, nullable=False, comment='更新时间戳')
    remark = Column(Text, default='', comment='备注')
    
    __table_args__ = (
        Index('idx_account_platform_status', 'platform', 'status'),
    )


class ProxyPool(Base):
    """代理池表 - 存储代理IP及其质量指标"""
    __tablename__ = 'proxy_pool'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_id = Column(String(64), nullable=False, unique=True, index=True, comment='代理唯一ID')
    ip = Column(String(64), nullable=False, comment='IP地址')
    port = Column(Integer, nullable=False, comment='端口')
    protocol = Column(String(16), default='http', comment='协议: http/https/socks5')
    username = Column(String(255), default='', comment='认证用户名')
    password = Column(String(255), default='', comment='认证密码')
    source = Column(String(64), default='manual', comment='来源: manual/api/file')
    country = Column(String(32), default='CN', comment='国家')
    province = Column(String(64), default='', comment='省份')
    city = Column(String(64), default='', comment='城市')
    isp = Column(String(64), default='', comment='运营商')
    status = Column(String(32), default='testing', index=True, comment='状态: online/offline/testing')
    is_active = Column(Integer, default=1, index=True, comment='是否激活 0/1')
    quality_score = Column(Float, default=50.0, index=True, comment='质量评分 0-100')
    response_time = Column(Integer, default=0, comment='响应时间(ms)')
    # 质量指标字段
    total_requests = Column(Integer, default=0, comment='总请求数')
    success_requests = Column(Integer, default=0, comment='成功请求数')
    failed_requests = Column(Integer, default=0, comment='失败请求数')
    consecutive_failures = Column(Integer, default=0, comment='连续失败次数')
    last_success_at = Column(BigInteger, default=0, comment='最后成功时间戳')
    last_failure_at = Column(BigInteger, default=0, comment='最后失败时间戳')
    last_checked_at = Column(BigInteger, default=0, comment='最后检测时间戳')
    expired_at = Column(BigInteger, default=0, comment='过期时间戳')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳')
    updated_at = Column(BigInteger, nullable=False, comment='更新时间戳')
    
    __table_args__ = (
        Index('idx_proxy_ip_port', 'ip', 'port', unique=True),
    )


class ProxyBinding(Base):
    """代理绑定表 - 记录账号与代理的绑定关系"""
    __tablename__ = 'proxy_binding'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    binding_id = Column(String(64), nullable=False, unique=True, index=True, comment='绑定唯一ID')
    account_id = Column(String(64), nullable=False, index=True, comment='账号ID')
    platform = Column(String(32), nullable=False, comment='平台')
    proxy_id = Column(String(64), nullable=False, index=True, comment='代理ID')
    is_sticky = Column(Integer, default=1, comment='是否粘性绑定 0/1')
    status = Column(String(32), default='active', comment='状态: active/inactive')
    rebind_count = Column(Integer, default=0, comment='重新绑定次数')
    bound_at = Column(BigInteger, nullable=False, comment='绑定时间戳')
    last_used_at = Column(BigInteger, default=0, comment='最后使用时间戳')
    
    __table_args__ = (
        Index('idx_binding_account_platform', 'account_id', 'platform', unique=True),
    )


class SystemConfig(Base):
    """系统配置表 - 存储系统级动态配置"""
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(128), nullable=False, unique=True, index=True, comment='配置键')
    config_value = Column(Text, default='', comment='配置值JSON')
    config_type = Column(String(32), default='system', index=True, comment='类型: proxy/crawler/system')
    description = Column(Text, default='', comment='配置描述')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳')
    updated_at = Column(BigInteger, nullable=False, comment='更新时间戳')
