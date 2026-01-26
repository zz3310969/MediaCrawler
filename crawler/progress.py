# -*- coding: utf-8 -*-
# @Desc    : 爬虫进度管理模块 - 支持断点续爬

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import aiofiles

from tools import utils


class CrawlStatus(Enum):
    """爬取状态枚举"""
    PENDING = "pending"        # 等待开始
    RUNNING = "running"        # 运行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


@dataclass
class CrawlProgress:
    """爬取进度状态数据类"""
    
    # 基本信息
    platform: str                          # 平台名称 (wb, xhs, dy, etc.)
    crawler_type: str                      # 爬取类型 (search/detail/creator/creator_vip)
    task_id: str = ""                      # 任务唯一ID
    started_at: str = ""                   # 开始时间
    updated_at: str = ""                   # 最后更新时间
    status: str = CrawlStatus.PENDING.value  # 任务状态
    
    # 搜索模式进度
    keywords: List[str] = field(default_factory=list)  # 关键词列表
    current_keyword_index: int = 0         # 当前关键词索引
    current_page: int = 1                  # 当前页码
    
    # 创作者模式进度
    creator_ids: List[str] = field(default_factory=list)  # 创作者ID列表
    current_creator_index: int = 0         # 当前创作者索引
    
    # VIP创作者模式进度
    vip_creator_ids: List[str] = field(default_factory=list)  # VIP创作者ID列表
    current_vip_creator_index: int = 0     # 当前VIP创作者索引
    
    # 详情模式进度
    note_ids: List[str] = field(default_factory=list)  # 帖子ID列表
    current_note_index: int = 0            # 当前帖子索引
    
    # 已处理的内容ID (用于去重和断点恢复)
    processed_note_ids: List[str] = field(default_factory=list)
    processed_comment_note_ids: List[str] = field(default_factory=list)
    
    # 统计信息
    total_notes_crawled: int = 0           # 已爬取帖子数
    total_comments_crawled: int = 0        # 已爬取评论数
    total_creators_crawled: int = 0        # 已爬取创作者数
    
    # 错误信息
    last_error: str = ""                   # 最后一次错误信息
    error_count: int = 0                   # 错误计数
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.task_id:
            self.task_id = self._generate_task_id()
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{self.platform}_{self.crawler_type}_{timestamp}_{short_uuid}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrawlProgress":
        """从字典创建实例"""
        # 确保列表字段是列表类型
        list_fields = [
            'keywords', 'creator_ids', 'vip_creator_ids', 'note_ids',
            'processed_note_ids', 'processed_comment_note_ids'
        ]
        for field_name in list_fields:
            if field_name in data and data[field_name] is None:
                data[field_name] = []
        return cls(**data)
    
    def is_note_processed(self, note_id: str) -> bool:
        """检查帖子是否已处理"""
        return note_id in self.processed_note_ids
    
    def mark_note_processed(self, note_id: str) -> None:
        """标记帖子为已处理"""
        if note_id not in self.processed_note_ids:
            self.processed_note_ids.append(note_id)
            self.total_notes_crawled += 1
    
    def is_comment_note_processed(self, note_id: str) -> bool:
        """检查帖子的评论是否已处理"""
        return note_id in self.processed_comment_note_ids
    
    def mark_comment_note_processed(self, note_id: str) -> None:
        """标记帖子评论为已处理"""
        if note_id not in self.processed_comment_note_ids:
            self.processed_comment_note_ids.append(note_id)
    
    def get_current_keyword(self) -> Optional[str]:
        """获取当前关键词"""
        if 0 <= self.current_keyword_index < len(self.keywords):
            return self.keywords[self.current_keyword_index]
        return None
    
    def get_remaining_keywords(self) -> List[str]:
        """获取剩余未处理的关键词"""
        return self.keywords[self.current_keyword_index:]
    
    def advance_keyword(self) -> bool:
        """前进到下一个关键词，返回是否还有更多关键词"""
        self.current_keyword_index += 1
        self.current_page = 1  # 重置页码
        return self.current_keyword_index < len(self.keywords)
    
    def get_current_creator_id(self) -> Optional[str]:
        """获取当前创作者ID"""
        if 0 <= self.current_creator_index < len(self.creator_ids):
            return self.creator_ids[self.current_creator_index]
        return None
    
    def advance_creator(self) -> bool:
        """前进到下一个创作者，返回是否还有更多创作者"""
        self.current_creator_index += 1
        self.total_creators_crawled += 1
        return self.current_creator_index < len(self.creator_ids)
    
    def get_current_vip_creator_id(self) -> Optional[str]:
        """获取当前VIP创作者ID"""
        if 0 <= self.current_vip_creator_index < len(self.vip_creator_ids):
            return self.vip_creator_ids[self.current_vip_creator_index]
        return None
    
    def advance_vip_creator(self) -> bool:
        """前进到下一个VIP创作者"""
        self.current_vip_creator_index += 1
        return self.current_vip_creator_index < len(self.vip_creator_ids)
    
    def record_error(self, error_msg: str) -> None:
        """记录错误"""
        self.last_error = error_msg
        self.error_count += 1
        self.updated_at = datetime.now().isoformat()


class ProgressManager:
    """进度管理器 - 负责进度的持久化存储和恢复"""
    
    def __init__(self, progress_dir: str = "./crawl_progress"):
        self.progress_dir = progress_dir
        self._ensure_dir_exists()
    
    def _ensure_dir_exists(self) -> None:
        """确保进度目录存在"""
        if not os.path.exists(self.progress_dir):
            os.makedirs(self.progress_dir, exist_ok=True)
    
    def _get_progress_file_path(self, platform: str, task_id: str) -> str:
        """获取进度文件路径"""
        return os.path.join(self.progress_dir, f"{task_id}.json")
    
    def _get_latest_progress_file(self, platform: str, crawler_type: str) -> Optional[str]:
        """获取最新的进度文件路径"""
        if not os.path.exists(self.progress_dir):
            return None
        
        # 查找匹配的进度文件
        prefix = f"{platform}_{crawler_type}_"
        matching_files = [
            f for f in os.listdir(self.progress_dir)
            if f.startswith(prefix) and f.endswith('.json')
        ]
        
        if not matching_files:
            return None
        
        # 按修改时间排序，返回最新的
        matching_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(self.progress_dir, f)),
            reverse=True
        )
        return os.path.join(self.progress_dir, matching_files[0])
    
    async def save_progress(self, progress: CrawlProgress) -> None:
        """保存进度到文件"""
        progress.updated_at = datetime.now().isoformat()
        file_path = self._get_progress_file_path(progress.platform, progress.task_id)
        
        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(progress.to_dict(), ensure_ascii=False, indent=2))
            utils.logger.debug(f"[ProgressManager] Progress saved to {file_path}")
        except Exception as e:
            utils.logger.error(f"[ProgressManager] Failed to save progress: {e}")
    
    async def load_progress(self, platform: str, task_id: str) -> Optional[CrawlProgress]:
        """加载指定任务的进度"""
        file_path = self._get_progress_file_path(platform, task_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                return CrawlProgress.from_dict(data)
        except Exception as e:
            utils.logger.error(f"[ProgressManager] Failed to load progress: {e}")
            return None
    
    async def load_latest_unfinished(self, platform: str, crawler_type: str) -> Optional[CrawlProgress]:
        """加载最新的未完成任务进度"""
        file_path = self._get_latest_progress_file(platform, crawler_type)
        
        if not file_path or not os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                progress = CrawlProgress.from_dict(data)
                
                # 只返回未完成的任务
                if progress.status in (CrawlStatus.RUNNING.value, CrawlStatus.PAUSED.value, CrawlStatus.PENDING.value):
                    utils.logger.info(f"[ProgressManager] Found unfinished task: {progress.task_id}")
                    return progress
                return None
        except Exception as e:
            utils.logger.error(f"[ProgressManager] Failed to load latest progress: {e}")
            return None
    
    async def mark_running(self, progress: CrawlProgress) -> None:
        """标记任务为运行中"""
        progress.status = CrawlStatus.RUNNING.value
        await self.save_progress(progress)
    
    async def mark_paused(self, progress: CrawlProgress) -> None:
        """标记任务为暂停"""
        progress.status = CrawlStatus.PAUSED.value
        await self.save_progress(progress)
    
    async def mark_completed(self, progress: CrawlProgress) -> None:
        """标记任务为完成"""
        progress.status = CrawlStatus.COMPLETED.value
        await self.save_progress(progress)
        utils.logger.info(f"[ProgressManager] Task {progress.task_id} completed")
    
    async def mark_failed(self, progress: CrawlProgress, error_msg: str = "") -> None:
        """标记任务为失败"""
        progress.status = CrawlStatus.FAILED.value
        if error_msg:
            progress.record_error(error_msg)
        await self.save_progress(progress)
        utils.logger.error(f"[ProgressManager] Task {progress.task_id} failed: {error_msg}")
    
    def list_all_progress(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有进度文件的摘要信息"""
        if not os.path.exists(self.progress_dir):
            return []
        
        result = []
        for filename in os.listdir(self.progress_dir):
            if not filename.endswith('.json'):
                continue
            
            if platform and not filename.startswith(f"{platform}_"):
                continue
            
            file_path = os.path.join(self.progress_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result.append({
                        'task_id': data.get('task_id'),
                        'platform': data.get('platform'),
                        'crawler_type': data.get('crawler_type'),
                        'status': data.get('status'),
                        'started_at': data.get('started_at'),
                        'updated_at': data.get('updated_at'),
                        'total_notes_crawled': data.get('total_notes_crawled', 0),
                        'total_comments_crawled': data.get('total_comments_crawled', 0),
                    })
            except Exception as e:
                utils.logger.warning(f"[ProgressManager] Failed to read {filename}: {e}")
        
        # 按更新时间排序
        result.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return result
    
    async def delete_progress(self, task_id: str) -> bool:
        """删除指定任务的进度文件"""
        # 查找匹配的文件
        if not os.path.exists(self.progress_dir):
            return False
        
        for filename in os.listdir(self.progress_dir):
            if task_id in filename:
                file_path = os.path.join(self.progress_dir, filename)
                try:
                    os.remove(file_path)
                    utils.logger.info(f"[ProgressManager] Deleted progress file: {filename}")
                    return True
                except Exception as e:
                    utils.logger.error(f"[ProgressManager] Failed to delete {filename}: {e}")
                    return False
        return False
    
    async def cleanup_completed(self, keep_days: int = 7) -> int:
        """清理已完成的旧进度文件"""
        if not os.path.exists(self.progress_dir):
            return 0
        
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        for filename in os.listdir(self.progress_dir):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(self.progress_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 只清理已完成的任务
                if data.get('status') != CrawlStatus.COMPLETED.value:
                    continue
                
                # 检查更新时间
                updated_at = data.get('updated_at', '')
                if updated_at:
                    update_time = datetime.fromisoformat(updated_at)
                    if update_time < cutoff_date:
                        os.remove(file_path)
                        deleted_count += 1
                        utils.logger.info(f"[ProgressManager] Cleaned up old progress: {filename}")
            except Exception as e:
                utils.logger.warning(f"[ProgressManager] Error processing {filename}: {e}")
        
        return deleted_count

