#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加增量爬取元数据表

使用方法:
    python database/migrations/migrate_incremental.py

说明:
    - 本脚本会自动检测数据库类型并执行迁移
    - 支持 SQLite, MySQL, PostgreSQL
    - 幂等性：多次执行不会出错
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text, inspect
from database.db_session import get_session
from database.models import Base, IncrementalMetadata
from tools import utils


async def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    async with get_session() as session:
        # 获取所有表名
        result = await session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
        ))
        return result.scalar() is not None


async def migrate():
    """执行数据库迁移"""
    utils.logger.info("=" * 60)
    utils.logger.info("开始执行数据库迁移 - 添加增量爬取元数据表")
    utils.logger.info("=" * 60)
    
    try:
        # 检查表是否已存在
        if await check_table_exists('incremental_metadata'):
            utils.logger.warning("⚠️  表 'incremental_metadata' 已存在，跳过创建")
            utils.logger.info("如需重新创建，请先手动删除该表")
            return
        
        # 创建表
        utils.logger.info("📝 正在创建表 'incremental_metadata'...")
        
        async with get_session() as session:
            # 使用SQLAlchemy的方式创建表
            # 注意：这里需要使用同步引擎来创建表
            from database.db import engine
            Base.metadata.create_all(engine, tables=[IncrementalMetadata.__table__])
            
        utils.logger.info("✅ 表创建成功！")
        
        # 验证迁移
        utils.logger.info("🔍 验证迁移结果...")
        async with get_session() as session:
            result = await session.execute(text(
                "SELECT COUNT(*) FROM incremental_metadata"
            ))
            count = result.scalar()
            utils.logger.info(f"✅ 验证成功！当前记录数: {count}")
        
        utils.logger.info("=" * 60)
        utils.logger.info("✨ 数据库迁移完成！")
        utils.logger.info("=" * 60)
        
    except Exception as e:
        utils.logger.error(f"❌ 数据库迁移失败: {e}")
        utils.logger.error("请检查数据库连接和配置")
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())

