#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
微信文章内容迁移工具

将数据库中的文章HTML内容迁移到本地文件系统，
以减少数据库体积并提升性能。

使用方法：
    python -m tools.migrate_wechat_content [--dry-run] [--batch-size=100]
    
参数：
    --dry-run       仅模拟执行，不实际迁移数据
    --batch-size    每批处理的文章数量，默认100
    --clear-db      迁移后清空数据库中的content字段
"""

import asyncio
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.content_storage import ContentStorage
from tools import utils


async def get_articles_to_migrate(session, batch_size: int, offset: int):
    """获取需要迁移的文章"""
    from database.models import WeChatArticle
    from sqlalchemy import select, and_, or_
    
    # 查找有content但没有content_path的文章
    stmt = select(WeChatArticle).where(
        and_(
            WeChatArticle.content != None,
            WeChatArticle.content != "",
            or_(
                WeChatArticle.content_path == None,
                WeChatArticle.content_path == ""
            )
        )
    ).offset(offset).limit(batch_size)
    
    result = await session.execute(stmt)
    return result.scalars().all()


async def count_articles_to_migrate(session) -> int:
    """统计需要迁移的文章数量"""
    from database.models import WeChatArticle
    from sqlalchemy import select, func, and_, or_
    
    stmt = select(func.count()).select_from(WeChatArticle).where(
        and_(
            WeChatArticle.content != None,
            WeChatArticle.content != "",
            or_(
                WeChatArticle.content_path == None,
                WeChatArticle.content_path == ""
            )
        )
    )
    
    result = await session.execute(stmt)
    return result.scalar() or 0


async def update_article_content_path(session, article_id: str, content_path: str, clear_content: bool = False):
    """更新文章的content_path字段"""
    from database.models import WeChatArticle
    from sqlalchemy import update
    
    update_data = {"content_path": content_path}
    if clear_content:
        update_data["content"] = ""
    
    stmt = update(WeChatArticle).where(
        WeChatArticle.article_id == article_id
    ).values(**update_data)
    
    await session.execute(stmt)


async def migrate_content(
    dry_run: bool = False,
    batch_size: int = 100,
    clear_db: bool = False
):
    """
    执行内容迁移
    
    Args:
        dry_run: 是否仅模拟执行
        batch_size: 每批处理数量
        clear_db: 是否清空数据库中的content字段
    """
    from database.db_session import get_session
    
    storage = ContentStorage(platform="wechat")
    
    print("=" * 60)
    print("微信文章内容迁移工具")
    print("=" * 60)
    
    if dry_run:
        print("[模拟模式] 不会实际修改数据")
    
    # 统计需要迁移的文章数量
    async with get_session() as session:
        total_count = await count_articles_to_migrate(session)
    
    if total_count == 0:
        print("\n没有需要迁移的文章，退出。")
        return
    
    print(f"\n发现 {total_count} 篇文章需要迁移")
    print(f"批次大小: {batch_size}")
    print(f"清空数据库content: {'是' if clear_db else '否'}")
    print("-" * 60)
    
    if not dry_run:
        confirm = input("\n确认开始迁移? (y/N): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
    
    # 统计信息
    migrated_count = 0
    failed_count = 0
    total_original_size = 0
    total_compressed_size = 0
    offset = 0
    
    while True:
        async with get_session() as session:
            articles = await get_articles_to_migrate(session, batch_size, 0)  # 始终从0开始，因为已迁移的会被过滤
            
            if not articles:
                break
            
            for article in articles:
                article_id = article.article_id
                fakeid = article.fakeid or ""
                content = article.content or ""
                
                if not content:
                    continue
                
                original_size = len(content.encode('utf-8'))
                total_original_size += original_size
                
                if dry_run:
                    # 模拟压缩计算
                    import gzip
                    compressed = gzip.compress(content.encode('utf-8'))
                    compressed_size = len(compressed)
                    total_compressed_size += compressed_size
                    
                    print(f"[模拟] {article_id[:20]}... "
                          f"原始: {original_size/1024:.1f}KB, "
                          f"压缩后: {compressed_size/1024:.1f}KB")
                    migrated_count += 1
                else:
                    try:
                        # 实际保存到文件
                        content_path = await storage.save_content(article_id, content, fakeid)
                        
                        if content_path:
                            # 更新数据库
                            await update_article_content_path(
                                session, article_id, content_path, clear_db
                            )
                            await session.commit()
                            
                            # 获取压缩后大小
                            compressed_size = storage.get_content_size(content_path)
                            total_compressed_size += compressed_size
                            
                            print(f"[迁移] {article_id[:20]}... "
                                  f"原始: {original_size/1024:.1f}KB, "
                                  f"压缩后: {compressed_size/1024:.1f}KB")
                            migrated_count += 1
                        else:
                            print(f"[失败] {article_id[:20]}... 保存文件失败")
                            failed_count += 1
                            
                    except Exception as e:
                        print(f"[错误] {article_id[:20]}... {e}")
                        failed_count += 1
                        await session.rollback()
        
        # 显示进度
        print(f"\n--- 已处理 {migrated_count + failed_count}/{total_count} ---\n")
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("迁移完成统计")
    print("=" * 60)
    print(f"总文章数: {total_count}")
    print(f"成功迁移: {migrated_count}")
    print(f"迁移失败: {failed_count}")
    print(f"原始总大小: {total_original_size/1024/1024:.2f} MB")
    print(f"压缩后总大小: {total_compressed_size/1024/1024:.2f} MB")
    
    if total_original_size > 0:
        saved = total_original_size - total_compressed_size
        ratio = (saved / total_original_size) * 100
        print(f"节省空间: {saved/1024/1024:.2f} MB ({ratio:.1f}%)")
    
    if not dry_run and clear_db:
        print("\n提示: 数据库中的content字段已清空，可以执行VACUUM命令回收空间")
        print("  SQLite: VACUUM;")
        print("  MySQL: OPTIMIZE TABLE wechat_article;")


def main():
    parser = argparse.ArgumentParser(
        description="微信文章内容迁移工具 - 将数据库内容迁移到本地文件"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅模拟执行，不实际迁移数据"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="每批处理的文章数量 (默认: 100)"
    )
    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="迁移后清空数据库中的content字段"
    )
    
    args = parser.parse_args()
    
    asyncio.run(migrate_content(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        clear_db=args.clear_db
    ))


if __name__ == "__main__":
    main()

