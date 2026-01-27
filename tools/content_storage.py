# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
文章内容本地文件存储工具

将大文本内容（如微信文章HTML）存储到本地文件系统，
数据库只保存文件路径，大幅减少数据库体积。

存储结构：
    data/
      wechat/
        content/
          {fakeid}/
            {article_id}.html.gz  # gzip压缩存储
"""

import gzip
import os
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional
from tools import utils


class ContentStorage:
    """文章内容本地文件存储管理器"""
    
    # 默认存储根目录
    DEFAULT_BASE_DIR = "data"
    
    def __init__(self, platform: str = "wechat", base_dir: Optional[str] = None):
        """
        初始化内容存储管理器
        
        Args:
            platform: 平台名称，如 wechat
            base_dir: 存储根目录，默认为 data
        """
        self.platform = platform
        self.base_dir = base_dir or self.DEFAULT_BASE_DIR
        self.content_dir = os.path.join(self.base_dir, platform, "content")
        
        # 确保目录存在
        Path(self.content_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_content_path(self, article_id: str, fakeid: str = "") -> str:
        """
        获取内容文件的完整路径
        
        Args:
            article_id: 文章ID
            fakeid: 公众号ID（可选，用于按公众号分目录）
            
        Returns:
            文件完整路径
        """
        if fakeid:
            # 按公众号分目录存储
            dir_path = os.path.join(self.content_dir, fakeid)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            return os.path.join(dir_path, f"{article_id}.html.gz")
        else:
            return os.path.join(self.content_dir, f"{article_id}.html.gz")
    
    def _get_relative_path(self, article_id: str, fakeid: str = "") -> str:
        """
        获取相对于项目根目录的路径（存储到数据库）
        
        Args:
            article_id: 文章ID
            fakeid: 公众号ID
            
        Returns:
            相对路径
        """
        if fakeid:
            return f"{self.base_dir}/{self.platform}/content/{fakeid}/{article_id}.html.gz"
        else:
            return f"{self.base_dir}/{self.platform}/content/{article_id}.html.gz"
    
    async def save_content(self, article_id: str, content: str, fakeid: str = "") -> str:
        """
        保存文章内容到本地文件（gzip压缩）
        
        Args:
            article_id: 文章ID
            content: 文章HTML内容
            fakeid: 公众号ID
            
        Returns:
            保存的相对路径
        """
        if not content:
            return ""
        
        file_path = self._get_content_path(article_id, fakeid)
        relative_path = self._get_relative_path(article_id, fakeid)
        
        try:
            # 使用gzip压缩存储
            compressed_content = gzip.compress(content.encode('utf-8'))
            
            # 异步写入文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(compressed_content)
            
            # 计算压缩率
            original_size = len(content.encode('utf-8'))
            compressed_size = len(compressed_content)
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            utils.logger.debug(
                f"[ContentStorage.save_content] Saved {article_id}, "
                f"original: {original_size/1024:.1f}KB, "
                f"compressed: {compressed_size/1024:.1f}KB, "
                f"ratio: {compression_ratio:.1f}%"
            )
            
            return relative_path
            
        except Exception as e:
            utils.logger.error(f"[ContentStorage.save_content] Failed to save {article_id}: {e}")
            return ""
    
    async def load_content(self, content_path: str) -> str:
        """
        从本地文件加载文章内容
        
        Args:
            content_path: 文件相对路径（从数据库读取）
            
        Returns:
            解压后的HTML内容
        """
        if not content_path:
            return ""
        
        try:
            # 异步读取文件
            async with aiofiles.open(content_path, 'rb') as f:
                compressed_content = await f.read()
            
            # 解压
            content = gzip.decompress(compressed_content).decode('utf-8')
            return content
            
        except FileNotFoundError:
            utils.logger.warning(f"[ContentStorage.load_content] File not found: {content_path}")
            return ""
        except Exception as e:
            utils.logger.error(f"[ContentStorage.load_content] Failed to load {content_path}: {e}")
            return ""
    
    def load_content_sync(self, content_path: str) -> str:
        """
        同步方式加载文章内容（用于非异步场景）
        
        Args:
            content_path: 文件相对路径
            
        Returns:
            解压后的HTML内容
        """
        if not content_path:
            return ""
        
        try:
            with gzip.open(content_path, 'rt', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            utils.logger.warning(f"[ContentStorage.load_content_sync] File not found: {content_path}")
            return ""
        except Exception as e:
            utils.logger.error(f"[ContentStorage.load_content_sync] Failed to load {content_path}: {e}")
            return ""
    
    async def delete_content(self, content_path: str) -> bool:
        """
        删除内容文件
        
        Args:
            content_path: 文件相对路径
            
        Returns:
            是否删除成功
        """
        if not content_path:
            return False
        
        try:
            if os.path.exists(content_path):
                os.remove(content_path)
                utils.logger.debug(f"[ContentStorage.delete_content] Deleted: {content_path}")
                return True
            return False
        except Exception as e:
            utils.logger.error(f"[ContentStorage.delete_content] Failed to delete {content_path}: {e}")
            return False
    
    def content_exists(self, article_id: str, fakeid: str = "") -> bool:
        """
        检查内容文件是否存在
        
        Args:
            article_id: 文章ID
            fakeid: 公众号ID
            
        Returns:
            是否存在
        """
        file_path = self._get_content_path(article_id, fakeid)
        return os.path.exists(file_path)
    
    def get_content_size(self, content_path: str) -> int:
        """
        获取内容文件大小（压缩后）
        
        Args:
            content_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            if os.path.exists(content_path):
                return os.path.getsize(content_path)
            return 0
        except Exception:
            return 0


# 全局单例
_wechat_content_storage: Optional[ContentStorage] = None


def get_wechat_content_storage() -> ContentStorage:
    """获取微信内容存储单例"""
    global _wechat_content_storage
    if _wechat_content_storage is None:
        _wechat_content_storage = ContentStorage(platform="wechat")
    return _wechat_content_storage

