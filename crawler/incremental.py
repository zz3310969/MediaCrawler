# -*- coding: utf-8 -*-
# @Desc    : 增量爬取管理模块 - 支持智能增量爬取
#
# 设计理念：
# 1. 不强制依赖 incremental_metadata 表
# 2. 直接从现有数据源（DB/JSON/CSV）查询历史数据
# 3. 支持所有存储类型（db、json、csv、excel）
# 4. incremental_metadata 表仅作为可选的性能优化和统计功能

import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database.db_session import get_session
from database.models import (
    IncrementalMetadata, 
    XhsNote, XhsNoteComment,
    WeiboNote, WeiboNoteComment,
    DouyinAweme, DouyinAwemeComment,
    BilibiliVideo, BilibiliVideoComment,
    KuaishouVideo, KuaishouVideoComment,
)
from tools import utils
from tools.time_util import get_current_timestamp


# 平台模型映射
PLATFORM_MODEL_MAP = {
    'xhs': {'note': XhsNote, 'note_id_field': 'note_id', 'user_id_field': 'user_id', 'time_field': 'time', 'title_field': 'title'},
    'weibo': {'note': WeiboNote, 'note_id_field': 'note_id', 'user_id_field': 'user_id', 'time_field': 'create_time', 'title_field': 'content'},
    'dy': {'note': DouyinAweme, 'note_id_field': 'aweme_id', 'user_id_field': 'user_id', 'time_field': 'create_time', 'title_field': 'title'},
    'bili': {'note': BilibiliVideo, 'note_id_field': 'video_id', 'user_id_field': 'user_id', 'time_field': 'create_time', 'title_field': 'title'},
    'ks': {'note': KuaishouVideo, 'note_id_field': 'video_id', 'user_id_field': 'user_id', 'time_field': 'create_time', 'title_field': 'title'},
}


class CreatorIncrementalHandler:
    """
    创作者模式增量处理器 - 使用早停策略
    
    设计理念：
    - 不依赖额外的元数据表
    - 直接从现有数据源（DB/JSON/CSV）查询历史数据
    - 支持所有存储类型
    """
    
    def __init__(self, platform: str = "xhs", store_type: str = None):
        self.platform = platform
        # 自动检测存储类型
        if store_type is None:
            store_type = config.SAVE_DATA_OPTION
        self.store_type = store_type
        
        utils.logger.info(
            f"[CreatorIncremental] 初始化: 平台={platform}, "
            f"存储类型={store_type}"
        )
    
    async def get_last_crawled_note(self, creator_id: str) -> Optional[Dict]:
        """
        从现有数据源查询该创作者上次爬到的最新笔记
        支持 DB、JSON、CSV、Excel 等所有存储类型
        
        Args:
            creator_id: 创作者ID
            
        Returns:
            Dict: 包含 note_id, time, title 的字典，如果没有则返回 None
        """
        if self.store_type in ["db", "sqlite", "postgres"]:
            # 数据库模式：直接查询 xhs_note 表
            return await self._get_from_database(creator_id)
        
        elif self.store_type == "json":
            # JSON 模式：扫描 JSON 文件
            return await self._get_from_json(creator_id)
        
        elif self.store_type == "csv":
            # CSV 模式：读取 CSV 文件
            return await self._get_from_csv(creator_id)
        
        elif self.store_type == "excel":
            # Excel 模式：读取 Excel 文件
            return await self._get_from_excel(creator_id)
        
        else:
            utils.logger.warning(
                f"[CreatorIncremental] 不支持的存储类型: {self.store_type}"
            )
            return None
    
    async def _get_from_database(self, creator_id: str) -> Optional[Dict]:
        """从数据库查询最新笔记（支持所有平台）"""
        try:
            # 获取平台对应的模型配置
            model_config = PLATFORM_MODEL_MAP.get(self.platform)
            if not model_config:
                utils.logger.warning(f"[CreatorIncremental] 不支持的平台: {self.platform}")
                return None
            
            model_class = model_config['note']
            note_id_field = model_config['note_id_field']
            user_id_field = model_config['user_id_field']
            time_field = model_config['time_field']
            title_field = model_config['title_field']
            
            async with get_session() as session:
                # 动态构建查询
                user_id_column = getattr(model_class, user_id_field)
                time_column = getattr(model_class, time_field)
                
                stmt = (
                    select(model_class)
                    .where(user_id_column == creator_id)
                    .order_by(time_column.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                note = result.scalar_one_or_none()
                
                if note:
                    note_id = getattr(note, note_id_field)
                    note_time = getattr(note, time_field)
                    note_title = getattr(note, title_field, '') or ''
                    
                    # 处理标题（微博的content可能很长，截取前50字）
                    if len(note_title) > 50:
                        note_title = note_title[:50] + '...'
                    
                    return {
                        'note_id': str(note_id),  # 统一转为字符串
                        'time': int(note_time) if note_time else 0,
                        'title': note_title
                    }
        except Exception as e:
            utils.logger.error(f"[CreatorIncremental] 数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    async def _get_from_json(self, creator_id: str) -> Optional[Dict]:
        """从JSON文件扫描最新笔记"""
        import os
        from pathlib import Path
        
        try:
            # data/xhs/json/ 目录
            json_dir = Path(f"data/{self.platform}/json")
            if not json_dir.exists():
                utils.logger.debug(f"[CreatorIncremental] JSON目录不存在: {json_dir}")
                return None
            
            latest_note = None
            latest_time = 0
            
            # 遍历所有 JSON 文件（只查看笔记文件，通常以 note_ 或直接是ID命名）
            for json_file in json_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 检查是否是该创作者的笔记
                    if data.get('user_id') == creator_id:
                        note_time = data.get('time', 0)
                        if note_time > latest_time:
                            latest_time = note_time
                            latest_note = {
                                'note_id': data.get('note_id'),
                                'time': note_time,
                                'title': data.get('title', '')
                            }
                except (json.JSONDecodeError, KeyError):
                    continue
            
            if latest_note:
                utils.logger.debug(
                    f"[CreatorIncremental] JSON中找到最新笔记: {latest_note['note_id']}"
                )
            
            return latest_note
        except Exception as e:
            utils.logger.error(f"[CreatorIncremental] JSON扫描失败: {e}")
            return None
    
    async def _get_from_csv(self, creator_id: str) -> Optional[Dict]:
        """从CSV文件读取最新笔记"""
        import csv
        from pathlib import Path
        
        try:
            # data/xhs/csv/ 目录
            csv_dir = Path(f"data/{self.platform}/csv")
            if not csv_dir.exists():
                return None
            
            latest_note = None
            latest_time = 0
            
            # 查找内容CSV文件
            for csv_file in csv_dir.glob("*contents*.csv"):
                try:
                    with open(csv_file, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('user_id') == creator_id:
                                note_time = int(row.get('time', 0))
                                if note_time > latest_time:
                                    latest_time = note_time
                                    latest_note = {
                                        'note_id': row.get('note_id'),
                                        'time': note_time,
                                        'title': row.get('title', '')
                                    }
                except Exception:
                    continue
            
            return latest_note
        except Exception as e:
            utils.logger.error(f"[CreatorIncremental] CSV读取失败: {e}")
            return None
    
    async def _get_from_excel(self, creator_id: str) -> Optional[Dict]:
        """从Excel文件读取最新笔记"""
        # Excel 模式暂不实现，返回 None 表示不支持增量（会全量爬取）
        utils.logger.warning(
            f"[CreatorIncremental] Excel模式暂不支持增量，将全量爬取"
        )
        return None
    
    
    async def should_stop_crawling(self, note_id: str, creator_id: str) -> bool:
        """
        判断是否应该停止爬取（该笔记是否已存在）
        支持所有存储类型
        
        Args:
            note_id: 笔记ID
            creator_id: 创作者ID
            
        Returns:
            bool: True表示已存在，可以考虑停止
        """
        if self.store_type in ["db", "sqlite", "postgres"]:
            # 数据库模式
            return await self._check_in_database(note_id, creator_id)
        
        elif self.store_type == "json":
            # JSON 模式：检查文件是否存在
            return await self._check_in_json(note_id)
        
        elif self.store_type == "csv":
            # CSV 模式：扫描CSV文件
            return await self._check_in_csv(note_id, creator_id)
        
        else:
            # 不支持的类型，返回 False（不跳过）
            return False
    
    async def _check_in_database(self, note_id: str, creator_id: str) -> bool:
        """检查数据库中是否存在该笔记（支持所有平台）"""
        try:
            # 获取平台对应的模型配置
            model_config = PLATFORM_MODEL_MAP.get(self.platform)
            if not model_config:
                return False
            
            model_class = model_config['note']
            note_id_field = model_config['note_id_field']
            user_id_field = model_config['user_id_field']
            
            async with get_session() as session:
                # 动态构建查询
                note_id_column = getattr(model_class, note_id_field)
                user_id_column = getattr(model_class, user_id_field)
                
                stmt = select(note_id_column).where(
                    note_id_column == note_id,
                    user_id_column == creator_id
                )
                result = await session.execute(stmt)
                return result.first() is not None
        except Exception as e:
            utils.logger.debug(f"[CreatorIncremental] 检查笔记存在失败: {e}")
            return False
    
    async def _check_in_json(self, note_id: str) -> bool:
        """检查JSON文件是否存在该笔记"""
        from pathlib import Path
        
        try:
            # 通常笔记会单独保存为一个JSON文件
            json_file = Path(f"data/{self.platform}/json/{note_id}.json")
            if json_file.exists():
                return True
            
            # 如果不是单独文件，需要扫描所有文件（性能较差）
            json_dir = Path(f"data/{self.platform}/json")
            if not json_dir.exists():
                return False
            
            for json_file in json_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('note_id') == note_id:
                        return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False
    
    async def _check_in_csv(self, note_id: str, creator_id: str) -> bool:
        """检查CSV文件中是否存在该笔记"""
        import csv
        from pathlib import Path
        
        try:
            csv_dir = Path(f"data/{self.platform}/csv")
            if not csv_dir.exists():
                return False
            
            for csv_file in csv_dir.glob("*contents*.csv"):
                try:
                    with open(csv_file, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('note_id') == note_id and row.get('user_id') == creator_id:
                                return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False
    
    async def process_creator_notes(
        self, 
        creator_id: str, 
        notes_list: List[Dict],
        creator_name: str = ""
    ) -> List[Dict]:
        """
        处理创作者的笔记列表（带早停逻辑）
        
        Args:
            creator_id: 创作者ID
            notes_list: 笔记列表（从API获取，按时间倒序）
            creator_name: 创作者名称（用于日志）
            
        Returns:
            List[Dict]: 过滤后需要处理的新笔记列表
        """
        if not notes_list:
            return []
        
        # 获取上次爬到的最新笔记
        last_note = await self.get_last_crawled_note(creator_id)
        if last_note:
            utils.logger.info(
                f"[CreatorIncremental] 创作者 {creator_name or creator_id} "
                f"上次最新笔记: {last_note['note_id']} "
                f"标题: {last_note['title'][:30]}... "
                f"时间: {datetime.fromtimestamp(last_note['time']) if last_note['time'] else 'Unknown'}"
            )
        else:
            utils.logger.info(
                f"[CreatorIncremental] 创作者 {creator_name or creator_id} "
                f"首次爬取，将处理所有笔记"
            )
        
        new_notes = []
        stop_count = 0  # 连续遇到已存在笔记的计数
        early_stop_threshold = config.CREATOR_EARLY_STOP_THRESHOLD
        
        for idx, note in enumerate(notes_list):
            note_id = note.get('note_id')
            note_title = note.get('title', '')
            
            # 检查是否应该停止（笔记已存在）
            if await self.should_stop_crawling(note_id, creator_id):
                stop_count += 1
                utils.logger.debug(
                    f"[CreatorIncremental] 笔记 {note_id} ({note_title[:20]}...) "
                    f"已存在, stop_count: {stop_count}/{early_stop_threshold}"
                )
                
                # 连续N条已存在，说明后面都是旧内容，可以停止了
                if stop_count >= early_stop_threshold:
                    utils.logger.info(
                        f"[CreatorIncremental] 🛑 停止爬取创作者 {creator_name or creator_id} "
                        f"(连续 {early_stop_threshold} 条笔记已存在，剩余 {len(notes_list) - idx} 条已跳过)"
                    )
                    break
            else:
                # 发现新笔记，重置计数
                stop_count = 0
                new_notes.append(note)
                utils.logger.debug(
                    f"[CreatorIncremental] ✨ 发现新笔记: {note_id} ({note_title[:30]}...)"
                )
        
        utils.logger.info(
            f"[CreatorIncremental] 创作者 {creator_name or creator_id} 统计: "
            f"总计={len(notes_list)}, 新增={len(new_notes)}, "
            f"已跳过={len(notes_list) - len(new_notes)}"
        )
        
        return new_notes
    
    async def update_metadata(
        self, 
        creator_id: str,
        latest_note: Dict,
        total_new_crawled: int,
        creator_name: str = ""
    ) -> None:
        """
        （可选）更新增量元数据到 incremental_metadata 表
        
        说明：
        - 这是一个可选的性能优化功能
        - 如果 incremental_metadata 表不存在，会静默跳过
        - 主要用于记录统计信息，不影响增量功能本身
        
        Args:
            creator_id: 创作者ID
            latest_note: 本次爬取的最新笔记信息
            total_new_crawled: 本次新爬取的数量
            creator_name: 创作者名称
        """
        # 只有数据库模式才尝试写入元数据表（可选功能）
        if self.store_type not in ["db", "sqlite", "postgres"]:
            return
        
        if not latest_note:
            return
        
        try:
            current_ts = int(get_current_timestamp())
            note_id = latest_note.get('note_id')
            note_time = latest_note.get('time', 0)
            note_title = latest_note.get('title', '')
            
            async with get_session() as session:
                # 查询是否已有记录
                stmt = select(IncrementalMetadata).where(
                    IncrementalMetadata.platform == self.platform,
                    IncrementalMetadata.crawler_type == 'creator',
                    IncrementalMetadata.target_key == creator_id
                )
                result = await session.execute(stmt)
                metadata = result.scalar_one_or_none()
                
                if metadata:
                    # 更新现有元数据
                    if note_time >= (metadata.last_note_time or 0):
                        metadata.last_note_id = note_id
                        metadata.last_note_time = note_time
                        metadata.last_note_title = note_title
                    
                    metadata.last_crawl_time = current_ts
                    metadata.total_crawled += total_new_crawled
                    metadata.updated_at = current_ts
                    
                    utils.logger.debug(
                        f"[CreatorIncremental] 📊 更新统计: 创作者={creator_name or creator_id}, "
                        f"本次新增={total_new_crawled}, 累计={metadata.total_crawled}"
                    )
                else:
                    # 创建新元数据
                    metadata = IncrementalMetadata(
                        platform=self.platform,
                        crawler_type='creator',
                        target_key=creator_id,
                        target_value=json.dumps({'creator_name': creator_name}),
                        last_note_id=note_id,
                        last_note_time=note_time,
                        last_note_title=note_title,
                        last_crawl_time=current_ts,
                        total_crawled=total_new_crawled,
                        incremental_enabled=1,
                        created_at=current_ts,
                        updated_at=current_ts
                    )
                    session.add(metadata)
                    
                    utils.logger.debug(
                        f"[CreatorIncremental] 📝 创建统计记录: 创作者={creator_name or creator_id}"
                    )
                
                await session.commit()
        except Exception as e:
            # 元数据更新失败不影响主流程
            utils.logger.debug(
                f"[CreatorIncremental] 元数据更新跳过（可能表不存在）: {e}"
            )
    
    async def get_stats(self, creator_id: str) -> Optional[Dict]:
        """
        获取创作者的统计信息
        支持从现有数据源获取
        
        Args:
            creator_id: 创作者ID
            
        Returns:
            Dict: 统计信息
        """
        # 获取最新笔记
        last_note = await self.get_last_crawled_note(creator_id)
        if not last_note:
            return None
        
        # 基础统计
        stats = {
            'creator_id': creator_id,
            'last_note_id': last_note['note_id'],
            'last_note_time': last_note['time'],
            'last_note_title': last_note['title'],
        }
        
        # 如果是数据库模式，尝试获取更多统计
        if self.store_type in ["db", "sqlite", "postgres"]:
            try:
                model_config = PLATFORM_MODEL_MAP.get(self.platform)
                if model_config:
                    model_class = model_config['note']
                    note_id_field = model_config['note_id_field']
                    user_id_field = model_config['user_id_field']
                    
                    async with get_session() as session:
                        # 查询该创作者的总笔记数
                        note_id_column = getattr(model_class, note_id_field)
                        user_id_column = getattr(model_class, user_id_field)
                        
                        stmt = select(func.count(note_id_column)).where(
                            user_id_column == creator_id
                        )
                        result = await session.execute(stmt)
                        total_count = result.scalar()
                        stats['total_crawled'] = total_count
                    
                    # 尝试从元数据表获取额外信息（如果表存在）
                    try:
                        stmt = select(IncrementalMetadata).where(
                            IncrementalMetadata.platform == self.platform,
                            IncrementalMetadata.crawler_type == 'creator',
                            IncrementalMetadata.target_key == creator_id
                        )
                        result = await session.execute(stmt)
                        metadata = result.scalar_one_or_none()
                        if metadata:
                            stats['last_crawl_time'] = metadata.last_crawl_time
                            stats['created_at'] = metadata.created_at
                            stats['updated_at'] = metadata.updated_at
                    except Exception:
                        pass
            except Exception as e:
                utils.logger.debug(f"[CreatorIncremental] 获取统计失败: {e}")
        
        return stats


class SearchIncrementalHandler:
    """搜索模式增量处理器 - 时间/ID过滤策略（待实现）"""
    
    def __init__(self, platform: str = "xhs"):
        self.platform = platform
        utils.logger.info("[SearchIncremental] 搜索模式增量处理器（待实现）")


class DetailIncrementalHandler:
    """详情模式增量处理器 - 简单去重策略（待实现）"""
    
    def __init__(self, platform: str = "xhs"):
        self.platform = platform
        utils.logger.info("[DetailIncremental] 详情模式增量处理器（待实现）")

