# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/db.py
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

# persist-1<persist1@126.com>
# Reason: Refactored db.py into a module, removed direct execution entry point, fixed relative import issues.
# Side effects: None
# Rollback strategy: Restore this file.
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools import utils
from database.db_session import create_tables

async def init_table_schema(db_type: str):
    """
    Initializes the database table schema.
    This will create tables based on the ORM models.
    Args:
        db_type: The type of database, 'sqlite' or 'mysql'.
    """
    utils.logger.info(f"[init_table_schema] begin init {db_type} table schema ...")
    await create_tables(db_type)
    utils.logger.info(f"[init_table_schema] {db_type} table schema init successful")

async def init_db(db_type: str = None):
    await init_table_schema(db_type)

def _get_db_connection_info(db_type: str) -> str:
    """
    获取数据库连接信息字符串（隐藏密码）
    Args:
        db_type: 数据库类型
    Returns:
        str: 格式化的连接信息
    """
    from config.db_config import mysql_db_config, sqlite_db_config, postgres_db_config
    
    if db_type == "sqlite":
        return f"sqlite://{sqlite_db_config['db_path']}"
    elif db_type in ["mysql", "db"]:
        return f"mysql://{mysql_db_config['user']}:****@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
    elif db_type == "postgres":
        return f"postgresql://{postgres_db_config['user']}:****@{postgres_db_config['host']}:{postgres_db_config['port']}/{postgres_db_config['db_name']}"
    else:
        return f"{db_type}://unknown"


async def verify_connection(db_type: str = None) -> bool:
    """
    验证数据库连接是否正常
    Args:
        db_type: 数据库类型，如果为 None 则使用配置中的类型
    Returns:
        bool: 连接成功返回 True，否则返回 False
    """
    if db_type is None:
        import config
        db_type = config.SAVE_DATA_OPTION
    
    # 如果不是数据库模式，直接返回 True
    if db_type in ["json", "csv", "excel"]:
        return True
    
    try:
        from database.db_session import get_async_engine
        from sqlalchemy import text
        
        # 获取并打印连接信息
        conn_info = _get_db_connection_info(db_type)
        utils.logger.info(f"[verify_connection] 正在验证 {db_type} 数据库连接...")
        utils.logger.info(f"[verify_connection] 连接地址: {conn_info}")
        
        engine = get_async_engine(db_type)
        if not engine:
            utils.logger.error(f"[verify_connection] 无法获取 {db_type} 数据库引擎")
            return False
        
        # 尝试执行简单查询来验证连接
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        utils.logger.info(f"[verify_connection] {db_type} 数据库连接验证成功 ✓")
        return True
        
    except Exception as e:
        utils.logger.error(f"[verify_connection] {db_type} 数据库连接验证失败: {e}")
        utils.logger.error(f"[verify_connection] 连接地址: {conn_info}")
        return False

async def close():
    """
    Placeholder for closing database connections if needed in the future.
    """
    pass
