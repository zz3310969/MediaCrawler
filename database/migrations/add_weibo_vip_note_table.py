#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加 weibo_vip_note 表的数据库迁移脚本
用于支持微博VIP内容的增量爬取功能
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import config
from database.db_session import get_async_engine, create_database_if_not_exists
from sqlalchemy import text
from tools import utils


async def check_table_exists(engine, table_name: str) -> bool:
    """检查表是否已存在"""
    async with engine.connect() as conn:
        if config.SAVE_DATA_OPTION == "sqlite":
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
                {"table_name": table_name}
            )
        elif config.SAVE_DATA_OPTION in ["db", "mysql"]:
            result = await conn.execute(
                text("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME=:table_name"),
                {"table_name": table_name}
            )
        elif config.SAVE_DATA_OPTION == "postgres":
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename=:table_name"),
                {"table_name": table_name}
            )
        else:
            return False
        
        return result.first() is not None


async def create_weibo_vip_note_table():
    """创建 weibo_vip_note 表"""
    db_type = config.SAVE_DATA_OPTION
    
    if db_type not in ["db", "mysql", "sqlite", "postgres"]:
        utils.logger.error(f"[Migration] 不支持的数据库类型: {db_type}")
        return False
    
    utils.logger.info(f"[Migration] 正在为 {db_type} 创建 weibo_vip_note 表...")
    
    try:
        # 确保数据库存在
        await create_database_if_not_exists(db_type)
        
        # 获取引擎
        engine = get_async_engine(db_type)
        
        # 检查表是否已存在
        if await check_table_exists(engine, "weibo_vip_note"):
            utils.logger.info(f"[Migration] 表 weibo_vip_note 已存在，跳过创建")
            return True
        
        # 根据不同数据库类型创建表
        if db_type == "sqlite":
            create_sql = """
            CREATE TABLE IF NOT EXISTS weibo_vip_note (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                add_ts BIGINT,
                last_modify_ts BIGINT,
                note_id VARCHAR(255),
                oid VARCHAR(255),
                vuid VARCHAR(255),
                content TEXT,
                note_url TEXT,
                scheme TEXT,
                page_view TEXT,
                poster_url TEXT,
                poster_local_path TEXT DEFAULT '',
                poster_oss_url TEXT DEFAULT '',
                content_type INTEGER DEFAULT 0,
                money TEXT DEFAULT '',
                date TEXT DEFAULT '',
                source_keyword TEXT DEFAULT ''
            );
            """
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_note_id ON weibo_vip_note(note_id);",
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_oid ON weibo_vip_note(oid);",
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_vuid ON weibo_vip_note(vuid);"
            ]
        
        elif db_type in ["db", "mysql"]:
            create_sql = """
            CREATE TABLE IF NOT EXISTS weibo_vip_note (
                id INT AUTO_INCREMENT PRIMARY KEY,
                add_ts BIGINT,
                last_modify_ts BIGINT,
                note_id VARCHAR(255),
                oid VARCHAR(255),
                vuid VARCHAR(255),
                content TEXT,
                note_url TEXT,
                scheme TEXT,
                page_view TEXT,
                poster_url TEXT,
                poster_local_path TEXT DEFAULT '',
                poster_oss_url TEXT DEFAULT '',
                content_type INT DEFAULT 0,
                money TEXT,
                date TEXT,
                source_keyword TEXT,
                INDEX idx_note_id (note_id),
                INDEX idx_oid (oid),
                INDEX idx_vuid (vuid)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            index_sqls = []
        
        elif db_type == "postgres":
            create_sql = """
            CREATE TABLE IF NOT EXISTS weibo_vip_note (
                id SERIAL PRIMARY KEY,
                add_ts BIGINT,
                last_modify_ts BIGINT,
                note_id VARCHAR(255),
                oid VARCHAR(255),
                vuid VARCHAR(255),
                content TEXT,
                note_url TEXT,
                scheme TEXT,
                page_view TEXT,
                poster_url TEXT,
                poster_local_path TEXT DEFAULT '',
                poster_oss_url TEXT DEFAULT '',
                content_type INTEGER DEFAULT 0,
                money TEXT DEFAULT '',
                date TEXT DEFAULT '',
                source_keyword TEXT DEFAULT ''
            );
            """
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_note_id ON weibo_vip_note(note_id);",
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_oid ON weibo_vip_note(oid);",
                "CREATE INDEX IF NOT EXISTS idx_weibo_vip_note_vuid ON weibo_vip_note(vuid);"
            ]
        
        # 执行创建表语句
        async with engine.begin() as conn:
            await conn.execute(text(create_sql))
            utils.logger.info(f"[Migration] 表 weibo_vip_note 创建成功")
            
            # 创建索引
            for index_sql in index_sqls:
                await conn.execute(text(index_sql))
            
            if index_sqls:
                utils.logger.info(f"[Migration] 索引创建成功")
        
        # 验证表是否创建成功
        if await check_table_exists(engine, "weibo_vip_note"):
            utils.logger.info(f"[Migration] ✓ 表 weibo_vip_note 验证成功")
            return True
        else:
            utils.logger.error(f"[Migration] ✗ 表 weibo_vip_note 验证失败")
            return False
    
    except Exception as e:
        utils.logger.error(f"[Migration] 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("微博VIP笔记表迁移脚本")
    print("=" * 60)
    print(f"\n当前数据库类型: {config.SAVE_DATA_OPTION}")
    print(f"目标表: weibo_vip_note\n")
    
    if config.SAVE_DATA_OPTION not in ["db", "mysql", "sqlite", "postgres"]:
        print(f"⚠️  当前存储类型 ({config.SAVE_DATA_OPTION}) 不需要数据库表")
        print("只有数据库模式需要运行此迁移脚本")
        return 0
    
    print("正在执行迁移...\n")
    
    success = await create_weibo_vip_note_table()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 迁移成功完成！")
        print("\n现在可以使用微博VIP增量爬取功能了：")
        print("  python main.py --platform wb --type creator_vip --vip_creator_id YOUR_VUID")
    else:
        print("❌ 迁移失败，请检查错误信息")
        return 1
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

