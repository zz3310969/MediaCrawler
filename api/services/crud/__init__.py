# -*- coding: utf-8 -*-
"""
CRUD服务层
提供数据库操作的基础服务
"""

from .base import CRUDBase, generate_uuid, get_timestamp_seconds
from .user import UserCRUD, user_crud
from .account import AccountCRUD, account_crud
from .proxy import ProxyCRUD, proxy_crud, ProxyBindingCRUD, proxy_binding_crud
from .system_config import SystemConfigCRUD, system_config_crud, ConfigKeys, DEFAULT_CONFIGS
from .task import TaskCRUD, task_crud, TaskLogCRUD, task_log_crud

__all__ = [
    # Base
    "CRUDBase",
    "generate_uuid",
    "get_timestamp_seconds",
    # User
    "UserCRUD",
    "user_crud",
    # Account
    "AccountCRUD",
    "account_crud",
    # Proxy
    "ProxyCRUD",
    "proxy_crud",
    "ProxyBindingCRUD",
    "proxy_binding_crud",
    # System Config
    "SystemConfigCRUD",
    "system_config_crud",
    "ConfigKeys",
    "DEFAULT_CONFIGS",
    # Task
    "TaskCRUD",
    "task_crud",
    "TaskLogCRUD",
    "task_log_crud",
]
