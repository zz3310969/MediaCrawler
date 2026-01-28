# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
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

from typing import Dict, List

import config
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class WeChatStoreFactory:
    """微信存储工厂类"""
    
    STORES = {
        "csv": WeChatCsvStoreImplement,
        "json": WeChatJsonStoreImplement,
        "db": WeChatDbStoreImplement,
        "postgres": WeChatDbStoreImplement,
        "sqlite": WeChatSqliteStoreImplement,
        "excel": WeChatExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = WeChatStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                f"[WeChatStoreFactory.create_store] Invalid save option: {config.SAVE_DATA_OPTION}. "
                "Supported options: csv, json, db, postgres, sqlite, excel"
            )
        return store_class()


async def update_wechat_article(article_item: Dict) -> str:
    """
    保存微信文章
    
    Args:
        article_item: 文章数据字典
        
    Returns:
        str: "inserted" 表示新增, "updated" 表示更新, "error" 表示失败
    """
    if not article_item:
        utils.logger.warning(f"[store.wechat.update_wechat_article] ⚠️ 文章数据为空，跳过保存")
        return "error"
    
    article_id = article_item.get("article_id", "")
    title = article_item.get("title", "Unknown")
    fakeid = article_item.get("fakeid", "")
    
    if not article_id:
        utils.logger.warning(f"[store.wechat.update_wechat_article] ⚠️ 文章ID为空，跳过保存: title={title[:30]}")
        return "error"
    
    save_item = {
        "article_id": article_id,
        "title": title,
        "link": article_item.get("link", ""),
        "cover": article_item.get("cover", ""),
        "digest": article_item.get("digest", ""),
        "create_time": article_item.get("create_time", 0),
        "update_time": article_item.get("update_time", 0),
        "author": article_item.get("author", ""),
        "fakeid": fakeid,
        "account_name": article_item.get("account_name", ""),
        "content": article_item.get("content", ""),
        "read_num": article_item.get("read_num", 0),
        "like_num": article_item.get("like_num", 0),
        "comment_count": article_item.get("comment_count", 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "source_keyword": source_keyword_var.get(),
    }
    
    utils.logger.info(f"[store.wechat.update_wechat_article] 准备保存: id={article_id}, fakeid={fakeid}, title={title[:30]}")
    
    try:
        result = await WeChatStoreFactory.create_store().store_content(content_item=save_item)
        if result == "inserted":
            utils.logger.info(f"[store.wechat.update_wechat_article] ✅ 新增成功: id={article_id}")
        elif result == "updated":
            utils.logger.info(f"[store.wechat.update_wechat_article] ✅ 更新成功: id={article_id}")
        else:
            utils.logger.warning(f"[store.wechat.update_wechat_article] ⚠️ 保存结果未知: id={article_id}, result={result}")
        return result or "error"
    except Exception as e:
        utils.logger.error(f"[store.wechat.update_wechat_article] ❌ 保存失败: id={article_id}, error={e}")
        import traceback
        utils.logger.error(f"[store.wechat.update_wechat_article] 堆栈信息: {traceback.format_exc()}")
        raise  # 重新抛出异常，让上层知道保存失败


async def batch_update_wechat_articles(article_list: List[Dict]):
    """
    批量保存微信文章
    
    Args:
        article_list: 文章列表
    """
    if not article_list:
        return
    
    for article in article_list:
        await update_wechat_article(article)


async def update_wechat_comment(article_id: str, comment_item: Dict):
    """
    保存微信文章评论
    
    Args:
        article_id: 文章ID
        comment_item: 评论数据
    """
    if not comment_item or not article_id:
        return
    
    comment_id = comment_item.get("comment_id", "")
    
    save_item = {
        "comment_id": comment_id,
        "article_id": article_id,
        "content": comment_item.get("content", ""),
        "create_time": comment_item.get("create_time", 0),
        "like_num": comment_item.get("like_num", 0),
        "nick_name": comment_item.get("nick_name", ""),
        "logo_url": comment_item.get("logo_url", ""),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    
    utils.logger.info(f"[store.wechat.update_wechat_comment] comment: {comment_id}, article: {article_id}")
    await WeChatStoreFactory.create_store().store_comment(comment_item=save_item)


async def batch_update_wechat_comments(article_id: str, comments: List[Dict]):
    """
    批量保存评论
    
    Args:
        article_id: 文章ID
        comments: 评论列表
    """
    if not comments:
        return
    
    for comment in comments:
        await update_wechat_comment(article_id, comment)


async def save_wechat_account(account_item: Dict):
    """
    保存公众号信息
    
    Args:
        account_item: 公众号数据
    """
    if not account_item:
        return
    
    fakeid = account_item.get("fakeid", "")
    
    save_item = {
        "fakeid": fakeid,
        "nickname": account_item.get("nickname", ""),
        "alias": account_item.get("alias", ""),
        "round_head_img": account_item.get("round_head_img", ""),
        "service_type": account_item.get("service_type", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    
    utils.logger.info(f"[store.wechat.save_wechat_account] account: {fakeid}, name: {save_item['nickname']}")
    await WeChatStoreFactory.create_store().store_creator(creator=save_item)


async def get_wechat_article_content(article_id: str) -> str:
    """
    获取微信文章的HTML内容（兼容文件存储和数据库存储）
    
    Args:
        article_id: 文章ID
        
    Returns:
        文章HTML内容
    """
    from database.db_session import get_session
    from database.models import WeChatArticle
    from sqlalchemy import select
    from tools.content_storage import get_wechat_content_storage
    
    async with get_session() as session:
        stmt = select(WeChatArticle).where(WeChatArticle.article_id == article_id)
        result = await session.execute(stmt)
        article = result.scalar_one_or_none()
        
        if not article:
            return ""
        
        # 优先从文件读取
        if article.content_path:
            storage = get_wechat_content_storage()
            content = await storage.load_content(article.content_path)
            if content:
                return content
        
        # 回退到数据库内容
        return article.content or ""


def get_wechat_article_content_sync(article_id: str) -> str:
    """
    同步方式获取微信文章的HTML内容
    
    Args:
        article_id: 文章ID
        
    Returns:
        文章HTML内容
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在异步上下文中，使用线程池
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_wechat_article_content(article_id)
                )
                return future.result()
        else:
            return loop.run_until_complete(get_wechat_article_content(article_id))
    except RuntimeError:
        return asyncio.run(get_wechat_article_content(article_id))

