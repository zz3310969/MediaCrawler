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

from typing import Dict

import config
from base.base_crawler import AbstractStore
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var
from store.excel_store_base import ExcelStoreBase


class WeChatCsvStoreImplement(AbstractStore):
    """微信CSV存储实现"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="wechat", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """存储文章内容"""
        await self.writer.write_to_csv(item_type="articles", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        """存储公众号信息"""
        await self.writer.write_to_csv(item_type="accounts", item=creator)


class WeChatJsonStoreImplement(AbstractStore):
    """微信JSON存储实现"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="wechat", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """存储文章内容"""
        await self.writer.write_to_json(item_type="articles", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        await self.writer.write_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        """存储公众号信息"""
        await self.writer.write_to_json(item_type="accounts", item=creator)


class WeChatDbStoreImplement(AbstractStore):
    """微信数据库存储实现"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._content_storage = None
    
    def _get_content_storage(self):
        """延迟初始化内容存储器"""
        if self._content_storage is None:
            from tools.content_storage import ContentStorage
            from config import wechat_config
            base_dir = getattr(wechat_config, 'CONTENT_STORAGE_BASE_DIR', 'data')
            self._content_storage = ContentStorage(platform="wechat", base_dir=base_dir)
        return self._content_storage
    
    def _is_file_storage_enabled(self) -> bool:
        """检查是否启用文件存储"""
        from config import wechat_config
        return getattr(wechat_config, 'ENABLE_CONTENT_FILE_STORAGE', True)
    
    async def _save_content_to_file(self, article_id: str, content: str, fakeid: str = "") -> str:
        """保存内容到文件，返回文件路径"""
        if not content or not self._is_file_storage_enabled():
            return ""
        
        storage = self._get_content_storage()
        return await storage.save_content(article_id, content, fakeid)
    
    async def store_content(self, content_item: Dict) -> str:
        """
        存储文章内容到数据库
        
        Returns:
            str: "inserted" 表示新增, "updated" 表示更新, "error" 表示失败
        """
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, update, and_
        from tools import utils
        
        article_id = content_item.get("article_id")
        fakeid = content_item.get("fakeid", "")
        title = content_item.get("title", "")[:1000]
        
        if not article_id:
            utils.logger.warning(f"[WeChatDbStoreImplement.store_content] ⚠️ 文章ID为空，跳过保存")
            return "error"
        
        if not fakeid:
            utils.logger.warning(f"[WeChatDbStoreImplement.store_content] ⚠️ fakeid为空，跳过保存: id={article_id}")
            return "error"
        
        utils.logger.info(f"[WeChatDbStoreImplement.store_content] 开始存储: id={article_id}, fakeid={fakeid}, title={title}")
        
        async with get_session() as session:
            if session is None:
                utils.logger.error(f"[WeChatDbStoreImplement.store_content] ❌ 数据库会话为空，无法保存文章: id={article_id}")
                return "error"
            
            # 检查文章是否存在（使用 article_id + fakeid 组合条件）
            stmt = select(WeChatArticle).where(
                and_(
                    WeChatArticle.article_id == article_id,
                    WeChatArticle.fakeid == fakeid
                )
            )
            result = await session.execute(stmt)
            existing_article = result.scalar_one_or_none()
            
            if existing_article:
                # 更新现有文章
                utils.logger.info(f"[WeChatDbStoreImplement.store_content] 文章已存在，执行更新: id={article_id}, fakeid={fakeid}")
                await self._update_article(session, content_item)
                utils.logger.info(f"[WeChatDbStoreImplement.store_content] ✅ 更新完成: id={article_id}, fakeid={fakeid}")
                return "updated"
            else:
                # 添加新文章
                utils.logger.info(f"[WeChatDbStoreImplement.store_content] 文章不存在，执行新增: id={article_id}, fakeid={fakeid}")
                await self._add_article(session, content_item)
                utils.logger.info(f"[WeChatDbStoreImplement.store_content] ✅ 新增完成: id={article_id}, fakeid={fakeid}")
                return "inserted"
    
    async def _add_article(self, session, content_item: Dict):
        """添加新文章"""
        from database.models import WeChatArticle
        from tools import utils
        
        add_ts = int(utils.get_current_timestamp())
        last_modify_ts = int(utils.get_current_timestamp())
        
        article_id = content_item.get("article_id")
        fakeid = content_item.get("fakeid", "")
        content = content_item.get("content", "")
        
        # 根据配置决定存储方式
        content_path = ""
        db_content = ""
        
        if self._is_file_storage_enabled() and content:
            # 存储到文件
            content_path = await self._save_content_to_file(article_id, content, fakeid)
            if content_path:
                utils.logger.info(f"[WeChatDbStoreImplement._add_article] Content saved to file: {content_path}")
            else:
                # 文件存储失败，回退到数据库存储
                db_content = content
        else:
            # 直接存储到数据库
            db_content = content
        
        article = WeChatArticle(
            article_id=article_id,
            title=content_item.get("title", ""),
            link=content_item.get("link", ""),
            cover=content_item.get("cover", ""),
            digest=content_item.get("digest", ""),
            create_time=content_item.get("create_time", 0),
            update_time=content_item.get("update_time", 0),
            author=content_item.get("author", ""),
            fakeid=fakeid,
            account_name=content_item.get("account_name", ""),
            content=db_content,
            content_path=content_path,
            read_num=content_item.get("read_num", 0),
            like_num=content_item.get("like_num", 0),
            old_like_num=content_item.get("old_like_num", 0),
            share_num=content_item.get("share_num", 0),
            comment_count=content_item.get("comment_count", 0),
            source_keyword=content_item.get("source_keyword", ""),
            add_ts=add_ts,
            last_modify_ts=last_modify_ts,
        )
        session.add(article)
        utils.logger.info(f"[WeChatDbStoreImplement._add_article] Added article: {article_id}")
    
    async def _update_article(self, session, content_item: Dict):
        """更新现有文章"""
        from database.models import WeChatArticle
        from sqlalchemy import update, and_
        from tools import utils
        
        article_id = content_item.get("article_id")
        fakeid = content_item.get("fakeid", "")
        content = content_item.get("content", "")
        last_modify_ts = int(utils.get_current_timestamp())
        
        # 准备更新数据
        update_data = {
            "last_modify_ts": last_modify_ts,
            "read_num": content_item.get("read_num", 0),
            "like_num": content_item.get("like_num", 0),
            "old_like_num": content_item.get("old_like_num", 0),
            "share_num": content_item.get("share_num", 0),
            "comment_count": content_item.get("comment_count", 0),
        }
        
        # 如果有HTML内容，也更新
        if content:
            if self._is_file_storage_enabled():
                # 存储到文件
                content_path = await self._save_content_to_file(article_id, content, fakeid)
                if content_path:
                    update_data["content_path"] = content_path
                    update_data["content"] = ""  # 清空数据库中的内容
                else:
                    update_data["content"] = content
            else:
                update_data["content"] = content
        
        # 使用 article_id + fakeid 组合条件更新
        stmt = update(WeChatArticle).where(
            and_(
                WeChatArticle.article_id == article_id,
                WeChatArticle.fakeid == fakeid
            )
        ).values(**update_data)
        await session.execute(stmt)
        utils.logger.info(f"[WeChatDbStoreImplement._update_article] Updated article: id={article_id}, fakeid={fakeid}")

    async def store_comment(self, comment_item: Dict):
        """存储评论到数据库"""
        from database.db_session import get_session
        from database.models import WeChatComment, WeChatCommentReply
        from sqlalchemy import select
        from tools import utils
        import json
        
        if not comment_item:
            return
        
        comment_id = comment_item.get("comment_id")
        article_id = comment_item.get("article_id")
        
        if not comment_id or not article_id:
            return
        
        async with get_session() as session:
            # 检查评论是否存在
            stmt = select(WeChatComment).where(WeChatComment.comment_id == comment_id)
            result = await session.execute(stmt)
            existing_comment = result.scalar_one_or_none()
            
            if existing_comment:
                # 更新现有评论
                await self._update_comment(session, comment_item)
            else:
                # 添加新评论
                await self._add_comment(session, comment_item)
            
            # 处理回复
            reply_list = comment_item.get("reply_list", [])
            for reply in reply_list:
                await self._add_or_update_reply(session, reply, comment_id, article_id)
    
    async def _add_comment(self, session, comment_item: Dict):
        """添加新评论"""
        from database.models import WeChatComment
        from tools import utils
        
        add_ts = int(utils.get_current_timestamp())
        last_modify_ts = int(utils.get_current_timestamp())
        
        comment = WeChatComment(
            comment_id=comment_item.get("comment_id"),
            article_id=comment_item.get("article_id"),
            content=comment_item.get("content", ""),
            create_time=comment_item.get("create_time", 0),
            like_num=comment_item.get("like_num", 0),
            nick_name=comment_item.get("nick_name", ""),
            logo_url=comment_item.get("logo_url", ""),
            add_ts=add_ts,
            last_modify_ts=last_modify_ts,
        )
        session.add(comment)
        utils.logger.info(f"[WeChatDbStoreImplement._add_comment] Added comment: {comment_item.get('comment_id')}")
    
    async def _update_comment(self, session, comment_item: Dict):
        """更新现有评论"""
        from database.models import WeChatComment
        from sqlalchemy import update
        from tools import utils
        
        comment_id = comment_item.get("comment_id")
        last_modify_ts = int(utils.get_current_timestamp())
        
        update_data = {
            "last_modify_ts": last_modify_ts,
            "like_num": comment_item.get("like_num", 0),
        }
        
        stmt = update(WeChatComment).where(WeChatComment.comment_id == comment_id).values(**update_data)
        await session.execute(stmt)
        utils.logger.info(f"[WeChatDbStoreImplement._update_comment] Updated comment: {comment_id}")
    
    async def _add_or_update_reply(self, session, reply_item: Dict, comment_id: str, article_id: str):
        """添加或更新回复"""
        from database.models import WeChatCommentReply
        from sqlalchemy import select, update
        from tools import utils
        
        reply_id = reply_item.get("reply_id")
        if not reply_id:
            return
        
        # 检查回复是否存在
        stmt = select(WeChatCommentReply).where(WeChatCommentReply.reply_id == reply_id)
        result = await session.execute(stmt)
        existing_reply = result.scalar_one_or_none()
        
        if existing_reply:
            # 更新回复
            last_modify_ts = int(utils.get_current_timestamp())
            update_data = {
                "last_modify_ts": last_modify_ts,
                "like_num": reply_item.get("like_num", 0),
            }
            stmt = update(WeChatCommentReply).where(WeChatCommentReply.reply_id == reply_id).values(**update_data)
            await session.execute(stmt)
        else:
            # 添加新回复
            add_ts = int(utils.get_current_timestamp())
            last_modify_ts = int(utils.get_current_timestamp())
            
            reply = WeChatCommentReply(
                reply_id=reply_id,
                comment_id=comment_id,
                article_id=article_id,
                content=reply_item.get("content", ""),
                create_time=reply_item.get("create_time", 0),
                like_num=reply_item.get("like_num", 0),
                nick_name=reply_item.get("nick_name", ""),
                add_ts=add_ts,
                last_modify_ts=last_modify_ts,
            )
            session.add(reply)

    async def store_creator(self, creator: Dict):
        """存储公众号信息到数据库"""
        from database.db_session import get_session
        from database.models import WeChatAccount
        from sqlalchemy import select, update
        from tools import utils
        
        fakeid = creator.get("fakeid")
        if not fakeid:
            return
        
        async with get_session() as session:
            # 检查公众号是否存在
            stmt = select(WeChatAccount).where(WeChatAccount.fakeid == fakeid)
            result = await session.execute(stmt)
            existing_account = result.scalar_one_or_none()
            
            if existing_account:
                # 更新现有公众号
                last_modify_ts = int(utils.get_current_timestamp())
                update_data = {
                    "last_modify_ts": last_modify_ts,
                    "nickname": creator.get("nickname", ""),
                    "alias": creator.get("alias", ""),
                    "round_head_img": creator.get("round_head_img", ""),
                    "service_type": creator.get("service_type", 0),
                }
                
                # 如果有文章总数，也更新 (可能由爬虫提供)
                if "total_article_count" in creator:
                    update_data["total_article_count"] = creator["total_article_count"]
                
                stmt = update(WeChatAccount).where(WeChatAccount.fakeid == fakeid).values(**update_data)
                await session.execute(stmt)
                utils.logger.info(f"[WeChatDbStoreImplement.store_creator] Updated account: {fakeid}")
            else:
                # 添加新公众号
                add_ts = int(utils.get_current_timestamp())
                last_modify_ts = int(utils.get_current_timestamp())
                
                account = WeChatAccount(
                    fakeid=fakeid,
                    nickname=creator.get("nickname", ""),
                    alias=creator.get("alias", ""),
                    round_head_img=creator.get("round_head_img", ""),
                    service_type=creator.get("service_type", 0),
                    total_article_count=creator.get("total_article_count", 0),
                    add_ts=add_ts,
                    last_modify_ts=last_modify_ts,
                )
                session.add(account)
                utils.logger.info(f"[WeChatDbStoreImplement.store_creator] Added account: {fakeid}")


class WeChatSqliteStoreImplement(WeChatDbStoreImplement):
    """微信SQLite存储实现（继承自数据库存储）"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class WeChatExcelStoreImplement(ExcelStoreBase, AbstractStore):
    """微信Excel存储实现"""
    
    def __init__(self, **kwargs):
        super().__init__(platform="wechat", **kwargs)

    async def store_content(self, content_item: Dict):
        """存储文章内容"""
        await self.save_data_to_excel("articles", content_item)

    async def store_comment(self, comment_item: Dict):
        """存储评论"""
        await self.save_data_to_excel("comments", comment_item)

    async def store_creator(self, creator: Dict):
        """存储公众号信息"""
        await self.save_data_to_excel("accounts", creator)

