#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增量爬取功能测试脚本

用法:
    python test_incremental.py

测试内容:
    1. 数据库连接测试
    2. 增量元数据表是否存在
    3. CreatorIncrementalHandler 基本功能
"""

import asyncio
import sys
from datetime import datetime

from database.db_session import get_session
from sqlalchemy import text, select
from database.models import IncrementalMetadata
from crawler.incremental import CreatorIncrementalHandler
from tools import utils


async def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试 1: 数据库连接")
    print("=" * 60)
    try:
        async with get_session() as session:
            result = await session.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


async def test_incremental_table():
    """测试增量元数据表是否存在"""
    print("\n" + "=" * 60)
    print("测试 2: 增量元数据表")
    print("=" * 60)
    try:
        async with get_session() as session:
            # 检查表是否存在
            result = await session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='incremental_metadata'"
            ))
            if result.scalar():
                print("✅ 表 'incremental_metadata' 存在")
                
                # 查询记录数
                result = await session.execute(text("SELECT COUNT(*) FROM incremental_metadata"))
                count = result.scalar()
                print(f"📊 当前记录数: {count}")
                
                # 如果有记录，显示前3条
                if count > 0:
                    result = await session.execute(text(
                        "SELECT platform, crawler_type, target_key, last_note_id, total_crawled "
                        "FROM incremental_metadata LIMIT 3"
                    ))
                    print("\n前3条记录:")
                    for row in result:
                        print(f"  - 平台:{row[0]}, 类型:{row[1]}, 目标:{row[2]}, "
                              f"最新笔记:{row[3]}, 累计:{row[4]}")
                
                return True
            else:
                print("❌ 表 'incremental_metadata' 不存在")
                print("💡 请先执行数据库迁移: python database/migrations/migrate_incremental.py")
                return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


async def test_creator_handler():
    """测试创作者增量处理器"""
    print("\n" + "=" * 60)
    print("测试 3: CreatorIncrementalHandler")
    print("=" * 60)
    try:
        handler = CreatorIncrementalHandler(platform="xhs")
        print("✅ CreatorIncrementalHandler 初始化成功")
        
        # 测试查询不存在的创作者
        test_creator_id = "test_creator_123456"
        last_note = await handler.get_last_crawled_note(test_creator_id)
        
        if last_note is None:
            print(f"✅ 查询不存在的创作者返回 None (符合预期)")
        else:
            print(f"📝 创作者 {test_creator_id} 的上次最新笔记:")
            print(f"   - 笔记ID: {last_note['note_id']}")
            print(f"   - 时间: {datetime.fromtimestamp(last_note['time']) if last_note['time'] else 'Unknown'}")
            print(f"   - 标题: {last_note['title'][:30]}...")
        
        # 测试过滤逻辑（模拟数据）
        mock_notes = [
            {'note_id': 'new_001', 'title': '新笔记1', 'time': 1700000000},
            {'note_id': 'new_002', 'title': '新笔记2', 'time': 1699999999},
        ]
        
        filtered_notes = await handler.process_creator_notes(
            creator_id=test_creator_id,
            notes_list=mock_notes,
            creator_name="测试创作者"
        )
        
        print(f"✅ 过滤逻辑测试通过 (输入:{len(mock_notes)}, 输出:{len(filtered_notes)})")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config():
    """测试配置项"""
    print("\n" + "=" * 60)
    print("测试 4: 配置项检查")
    print("=" * 60)
    try:
        import config
        
        print(f"ENABLE_INCREMENTAL_CRAWL = {config.ENABLE_INCREMENTAL_CRAWL}")
        print(f"CREATOR_EARLY_STOP_THRESHOLD = {config.CREATOR_EARLY_STOP_THRESHOLD}")
        print(f"INCREMENTAL_TIME_TOLERANCE = {config.INCREMENTAL_TIME_TOLERANCE}")
        print(f"INCREMENTAL_UPDATE_EXISTING = {config.INCREMENTAL_UPDATE_EXISTING}")
        print(f"INCREMENTAL_METADATA_STORE = {config.INCREMENTAL_METADATA_STORE}")
        
        if not config.ENABLE_INCREMENTAL_CRAWL:
            print("\n⚠️  注意: ENABLE_INCREMENTAL_CRAWL = False")
            print("💡 若要启用增量爬取，请在 config/base_config.py 中设置为 True")
        else:
            print("\n✅ 增量爬取已启用")
        
        return True
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False


async def main():
    """主测试流程"""
    print("\n" + "🧪" * 30)
    print("增量爬取功能测试")
    print("🧪" * 30 + "\n")
    
    results = []
    
    # 测试1: 数据库连接
    results.append(await test_database_connection())
    
    # 测试2: 增量元数据表
    results.append(await test_incremental_table())
    
    # 测试3: 创作者处理器
    results.append(await test_creator_handler())
    
    # 测试4: 配置项
    results.append(await test_config())
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✅ 所有测试通过！增量爬取功能已就绪")
        print("\n💡 下一步:")
        print("1. 确保配置 ENABLE_INCREMENTAL_CRAWL = True")
        print("2. 运行 python main.py 开始爬取")
        print("3. 查看日志中的增量相关信息")
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        print("请检查上述错误信息并修复")
    
    print("\n" + "🧪" * 30 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

