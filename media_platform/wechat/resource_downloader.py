# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""微信公众号资源下载器 - 用于下载文章中的图片、视频、音频等资源"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from tools import utils


class WeChatResourceDownloader:
    """微信资源下载器"""
    
    def __init__(self, base_save_path: str = "data/wechat_resources"):
        """初始化资源下载器"""
        self.base_save_path = Path(base_save_path)
        self.base_save_path.mkdir(parents=True, exist_ok=True)
        self.downloaded_urls: Set[str] = set()
    
    async def download_article_resources(
        self,
        html_content: str,
        article_id: str,
        fakeid: str = "",
        timeout: int = 30
    ) -> Tuple[str, Dict[str, int]]:
        """
        下载文章中的所有资源
        
        Args:
            html_content: 文章HTML内容
            article_id: 文章ID
            fakeid: 公众号ID（可选）
            timeout: 下载超时时间
            
        Returns:
            (处理后的HTML, 资源统计字典)
        """
        utils.logger.info(f"[WeChatResourceDownloader] Processing article: {article_id}")
        
        # 创建文章专属目录
        if fakeid:
            article_dir = self.base_save_path / fakeid / article_id
        else:
            article_dir = self.base_save_path / article_id
        article_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 下载统计
        stats = {'images': 0, 'videos': 0, 'audios': 0}
        
        # 下载图片
        stats['images'] = await self._download_images(soup, article_dir, timeout)
        
        # 下载视频
        stats['videos'] = await self._download_videos(soup, article_dir, timeout)
        
        # 下载音频
        stats['audios'] = await self._download_audios(soup, article_dir, timeout)
        
        # 返回处理后的HTML
        return str(soup), stats
    
    async def _download_images(self, soup: BeautifulSoup, save_dir: Path, timeout: int) -> int:
        """下载图片资源"""
        count = 0
        img_dir = save_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        img_tags = soup.find_all('img')
        utils.logger.info(f"[WeChatResourceDownloader] Found {len(img_tags)} images")
        
        for idx, img_tag in enumerate(img_tags):
            img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-original')
            
            if not img_url or img_url.startswith('data:'):
                continue
            
            if img_url in self.downloaded_urls:
                count += 1
                continue
            
            try:
                local_path = await self._download_file(img_url, img_dir, f"img_{idx}", timeout)
                
                if local_path:
                    # 更新img标签的src为相对路径
                    rel_path = local_path.relative_to(save_dir.parent)
                    img_tag['src'] = str(rel_path)
                    if img_tag.get('data-src'):
                        img_tag['data-src'] = str(rel_path)
                    
                    self.downloaded_urls.add(img_url)
                    count += 1
                    
            except Exception as e:
                utils.logger.error(f"[WeChatResourceDownloader] Failed to download image: {e}")
        
        return count
    
    async def _download_videos(self, soup: BeautifulSoup, save_dir: Path, timeout: int) -> int:
        """下载视频资源"""
        count = 0
        video_dir = save_dir / "videos"
        video_dir.mkdir(exist_ok=True)
        
        video_tags = soup.find_all('video')
        utils.logger.info(f"[WeChatResourceDownloader] Found {len(video_tags)} videos")
        
        for idx, video_tag in enumerate(video_tags):
            video_url = video_tag.get('src') or video_tag.get('data-src')
            
            # 检查source标签
            if not video_url:
                source_tag = video_tag.find('source')
                if source_tag:
                    video_url = source_tag.get('src')
            
            if not video_url or video_url in self.downloaded_urls:
                continue
            
            try:
                local_path = await self._download_file(video_url, video_dir, f"video_{idx}", timeout * 3)
                
                if local_path:
                    rel_path = local_path.relative_to(save_dir.parent)
                    video_tag['src'] = str(rel_path)
                    
                    source_tag = video_tag.find('source')
                    if source_tag:
                        source_tag['src'] = str(rel_path)
                    
                    self.downloaded_urls.add(video_url)
                    count += 1
                    
            except Exception as e:
                utils.logger.error(f"[WeChatResourceDownloader] Failed to download video: {e}")
        
        return count
    
    async def _download_audios(self, soup: BeautifulSoup, save_dir: Path, timeout: int) -> int:
        """下载音频资源"""
        count = 0
        audio_dir = save_dir / "audios"
        audio_dir.mkdir(exist_ok=True)
        
        # 查找audio标签和微信自定义音频组件
        audio_tags = soup.find_all('audio') + soup.find_all('mpvoice')
        utils.logger.info(f"[WeChatResourceDownloader] Found {len(audio_tags)} audios")
        
        for idx, audio_tag in enumerate(audio_tags):
            audio_url = audio_tag.get('src') or audio_tag.get('data-src') or audio_tag.get('voice_encode_fileid')
            
            if not audio_url or audio_url in self.downloaded_urls:
                continue
            
            try:
                local_path = await self._download_file(audio_url, audio_dir, f"audio_{idx}", timeout * 2)
                
                if local_path:
                    rel_path = local_path.relative_to(save_dir.parent)
                    audio_tag['src'] = str(rel_path)
                    
                    self.downloaded_urls.add(audio_url)
                    count += 1
                    
            except Exception as e:
                utils.logger.error(f"[WeChatResourceDownloader] Failed to download audio: {e}")
        
        return count
    
    async def _download_file(
        self,
        url: str,
        save_dir: Path,
        filename_prefix: str,
        timeout: int
    ) -> Optional[Path]:
        """下载单个文件"""
        try:
            # 解析URL获取文件扩展名
            parsed_url = urlparse(url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1].lower()
            
            # 如果没有扩展名，根据URL推断
            if not ext or len(ext) > 5:
                if 'video' in url or 'mp4' in url:
                    ext = '.mp4'
                elif 'audio' in url or 'mp3' in url:
                    ext = '.mp3'
                else:
                    ext = '.jpg'
            
            filename = f"{filename_prefix}{ext}"
            local_path = save_dir / filename
            
            # 如果文件已存在，跳过
            if local_path.exists():
                return local_path
            
            # 下载文件
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    utils.logger.debug(f"[WeChatResourceDownloader] Downloaded: {filename}")
                    return local_path
                else:
                    utils.logger.warning(f"[WeChatResourceDownloader] HTTP {response.status_code}: {url}")
                    return None
                    
        except Exception as e:
            utils.logger.error(f"[WeChatResourceDownloader] Download error: {url[:50]}... - {e}")
            return None
    
    def clear_cache(self):
        """清空已下载资源缓存"""
        self.downloaded_urls.clear()
