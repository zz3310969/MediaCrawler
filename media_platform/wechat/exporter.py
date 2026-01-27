# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""微信公众号文章导出器

支持多种导出格式：
- HTML（完整打包，包含图片、样式等资源）
- Markdown
- TXT（纯文本）
- DOCX（Word文档）
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from tools import utils


class WeChatArticleExporter:
    """微信文章导出器"""
    
    def __init__(self, base_export_path: str = "data/wechat_exports"):
        """初始化导出器
        
        Args:
            base_export_path: 导出文件的基础路径
        """
        self.base_export_path = Path(base_export_path)
        self.base_export_path.mkdir(parents=True, exist_ok=True)
        self.downloaded_resources: Set[str] = set()
    
    async def export_article_html(
        self,
        html_content: str,
        article_info: Dict,
        include_comments: bool = False,
        comments: Optional[List[Dict]] = None,
        timeout: int = 30
    ) -> Tuple[str, Dict[str, int]]:
        """
        导出文章为完整的HTML包（包含所有资源）
        
        参考 wechat-article-exporter 的 exportHtmlFiles 实现
        
        Args:
            html_content: 文章HTML内容
            article_info: 文章信息字典，需包含 article_id, title, fakeid 等
            include_comments: 是否包含评论
            comments: 评论列表
            timeout: 下载超时时间
            
        Returns:
            (导出目录路径, 资源统计字典)
        """
        article_id = article_info.get("article_id", "unknown")
        title = article_info.get("title", "未知标题")
        fakeid = article_info.get("fakeid", "")
        
        # 清理文件名中的非法字符
        safe_title = self._sanitize_filename(title)
        
        # 创建导出目录
        if fakeid:
            export_dir = self.base_export_path / fakeid / f"{safe_title}_{article_id}"
        else:
            export_dir = self.base_export_path / f"{safe_title}_{article_id}"
        export_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = export_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        utils.logger.info(f"[WeChatArticleExporter] Exporting article to: {export_dir}")
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 资源统计
        stats = {'images': 0, 'styles': 0, 'backgrounds': 0}
        
        # URL到本地路径的映射
        url_map: Dict[str, str] = {}
        
        # 1. 下载所有图片
        img_count = await self._download_and_replace_images(soup, assets_dir, url_map, timeout)
        stats['images'] = img_count
        
        # 2. 下载所有样式表
        style_count = await self._download_and_replace_styles(soup, assets_dir, url_map, timeout)
        stats['styles'] = style_count
        
        # 3. 处理背景图片
        bg_count = await self._process_background_images(soup, html_content, assets_dir, url_map, timeout)
        stats['backgrounds'] = bg_count
        
        # 4. 处理HTML内容
        final_html = self._normalize_html(soup, article_info, include_comments, comments, url_map)
        
        # 5. 写入HTML文件
        html_file = export_dir / "index.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(final_html)
        
        utils.logger.info(
            f"[WeChatArticleExporter] Export complete: "
            f"images={stats['images']}, styles={stats['styles']}, backgrounds={stats['backgrounds']}"
        )
        
        return str(export_dir), stats
    
    async def _download_and_replace_images(
        self,
        soup: BeautifulSoup,
        assets_dir: Path,
        url_map: Dict[str, str],
        timeout: int
    ) -> int:
        """下载所有图片并替换URL"""
        count = 0
        img_dir = assets_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        img_tags = soup.find_all('img')
        utils.logger.info(f"[WeChatArticleExporter] Found {len(img_tags)} images")
        
        for idx, img_tag in enumerate(img_tags):
            # 获取图片URL（可能在src或data-src中）
            img_url = img_tag.get('data-src') or img_tag.get('src')
            
            if not img_url or img_url.startswith('data:'):
                continue
            
            # 检查是否已下载
            if img_url in url_map:
                rel_path = url_map[img_url]
                img_tag['src'] = rel_path
                if img_tag.get('data-src'):
                    img_tag['data-src'] = rel_path
                count += 1
                continue
            
            try:
                local_path = await self._download_resource(img_url, img_dir, f"img_{idx}", timeout)
                
                if local_path:
                    rel_path = f"./assets/images/{local_path.name}"
                    url_map[img_url] = rel_path
                    
                    # 更新img标签
                    img_tag['src'] = rel_path
                    if img_tag.get('data-src'):
                        img_tag['data-src'] = rel_path
                    
                    count += 1
                    
            except Exception as e:
                utils.logger.warning(f"[WeChatArticleExporter] Failed to download image: {e}")
        
        return count
    
    async def _download_and_replace_styles(
        self,
        soup: BeautifulSoup,
        assets_dir: Path,
        url_map: Dict[str, str],
        timeout: int
    ) -> int:
        """下载所有样式表并替换URL"""
        count = 0
        css_dir = assets_dir / "css"
        css_dir.mkdir(exist_ok=True)
        
        link_tags = soup.find_all('link', rel='stylesheet')
        utils.logger.info(f"[WeChatArticleExporter] Found {len(link_tags)} stylesheets")
        
        for idx, link_tag in enumerate(link_tags):
            css_url = link_tag.get('href')
            
            if not css_url:
                continue
            
            if css_url in url_map:
                link_tag['href'] = url_map[css_url]
                count += 1
                continue
            
            try:
                local_path = await self._download_resource(css_url, css_dir, f"style_{idx}", timeout)
                
                if local_path:
                    rel_path = f"./assets/css/{local_path.name}"
                    url_map[css_url] = rel_path
                    link_tag['href'] = rel_path
                    count += 1
                    
            except Exception as e:
                utils.logger.warning(f"[WeChatArticleExporter] Failed to download stylesheet: {e}")
        
        return count
    
    async def _process_background_images(
        self,
        soup: BeautifulSoup,
        original_html: str,
        assets_dir: Path,
        url_map: Dict[str, str],
        timeout: int
    ) -> int:
        """处理CSS背景图片"""
        count = 0
        bg_dir = assets_dir / "backgrounds"
        bg_dir.mkdir(exist_ok=True)
        
        # 查找背景图片URL
        bg_pattern = r'(?:background|background-image)\s*:\s*url\(["\']?(https?://[^"\')\s]+)["\']?\)'
        bg_matches = re.findall(bg_pattern, original_html, re.IGNORECASE)
        
        utils.logger.info(f"[WeChatArticleExporter] Found {len(bg_matches)} background images")
        
        for idx, bg_url in enumerate(set(bg_matches)):
            if bg_url in url_map:
                continue
            
            try:
                local_path = await self._download_resource(bg_url, bg_dir, f"bg_{idx}", timeout)
                
                if local_path:
                    rel_path = f"./assets/backgrounds/{local_path.name}"
                    url_map[bg_url] = rel_path
                    count += 1
                    
            except Exception as e:
                utils.logger.warning(f"[WeChatArticleExporter] Failed to download background: {e}")
        
        return count
    
    async def _download_resource(
        self,
        url: str,
        save_dir: Path,
        filename_prefix: str,
        timeout: int
    ) -> Optional[Path]:
        """下载单个资源文件"""
        try:
            # 解析URL获取文件扩展名
            parsed_url = urlparse(url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1].lower()
            
            # 如果没有扩展名，根据URL推断
            if not ext or len(ext) > 5:
                if 'css' in url:
                    ext = '.css'
                elif 'video' in url or 'mp4' in url:
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
                    
                    return local_path
                else:
                    utils.logger.warning(f"[WeChatArticleExporter] HTTP {response.status_code}: {url[:50]}...")
                    return None
                    
        except Exception as e:
            utils.logger.error(f"[WeChatArticleExporter] Download error: {url[:50]}... - {e}")
            return None
    
    def _normalize_html(
        self,
        soup: BeautifulSoup,
        article_info: Dict,
        include_comments: bool,
        comments: Optional[List[Dict]],
        url_map: Dict[str, str]
    ) -> str:
        """
        标准化HTML内容
        
        - 处理懒加载图片
        - 移除无用元素
        - 渲染发布时间
        - 渲染阅读量
        - 添加评论
        """
        # 查找文章主内容区域
        js_article = soup.find(id='js_article')
        if not js_article:
            js_article = soup.find('div', class_='rich_media')
        
        if js_article:
            # 移除无用元素
            for selector in ['#js_top_ad_area', '#js_tags_preview_toast', '#content_bottom_area', 
                           '#js_pc_qr_code', '#wx_stream_article_slide_tip']:
                elem = js_article.select_one(selector)
                if elem:
                    elem.decompose()
            
            # 移除所有script标签
            for script in js_article.find_all('script'):
                script.decompose()
            
            # 确保 #js_content 可见
            js_content = js_article.find(id='js_content')
            if js_content and js_content.get('style'):
                del js_content['style']
        
        # 处理背景图片URL替换
        html_str = str(soup)
        for old_url, new_path in url_map.items():
            html_str = html_str.replace(old_url, new_path)
        
        # 构建完整的HTML页面
        title = article_info.get("title", "微信公众号文章")
        read_num = article_info.get("read_num", 0)
        like_num = article_info.get("like_num", 0)
        
        # 构建评论HTML
        comments_html = ""
        if include_comments and comments:
            comments_html = self._render_comments(comments)
        
        # 获取文章主内容
        page_content = str(js_article) if js_article else str(soup)
        
        # 构建本地样式链接
        local_styles = ""
        for old_url, new_path in url_map.items():
            if new_path.endswith('.css'):
                local_styles += f'<link rel="stylesheet" href="{new_path}">\n'
        
        final_html = f'''<!DOCTYPE html>
<html lang="zh_CN">
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=0,viewport-fit=cover">
    <title>{title}</title>
    {local_styles}
    <style>
        #page-content,
        #js_article_bottom_bar,
        .__page_content__ {{
            max-width: 667px;
            margin: 0 auto;
        }}
        img {{
            max-width: 100%;
        }}
        .article-stats {{
            padding: 10px 20px;
            color: #888;
            font-size: 14px;
            border-top: 1px solid #eee;
        }}
        .comments-section {{
            max-width: 667px;
            margin: 20px auto;
            padding: 20px;
            background: #f8f8f8;
            border-radius: 8px;
        }}
        .comments-section h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        .comment-item {{
            background: #fff;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
        }}
        .comment-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .comment-avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .comment-nickname {{
            font-weight: bold;
            color: #333;
        }}
        .comment-content {{
            color: #666;
            line-height: 1.6;
        }}
        .comment-meta {{
            margin-top: 10px;
            color: #999;
            font-size: 12px;
        }}
        .reply-list {{
            margin-left: 50px;
            margin-top: 10px;
            padding-left: 10px;
            border-left: 2px solid #eee;
        }}
        .reply-item {{
            padding: 10px 0;
        }}
    </style>
</head>
<body>
{page_content}

<!-- 文章统计 -->
<div class="article-stats">
    阅读 {read_num} · 在看 {like_num}
</div>

<!-- 评论数据 -->
{comments_html}
</body>
</html>'''
        
        return final_html
    
    def _render_comments(self, comments: List[Dict]) -> str:
        """渲染评论HTML"""
        if not comments:
            return ""
        
        html = '<div class="comments-section">\n'
        html += f'<h3>精选留言（{len(comments)}条）</h3>\n'
        
        for comment in comments:
            nick_name = comment.get("nick_name", "匿名用户")
            content = comment.get("content", "")
            like_num = comment.get("like_num", 0)
            logo_url = comment.get("logo_url", "")
            
            html += '<div class="comment-item">\n'
            html += '<div class="comment-header">\n'
            if logo_url:
                html += f'<img class="comment-avatar" src="{logo_url}" alt="">\n'
            html += f'<span class="comment-nickname">{nick_name}</span>\n'
            html += '</div>\n'
            html += f'<div class="comment-content">{content}</div>\n'
            html += f'<div class="comment-meta">👍 {like_num}</div>\n'
            
            # 渲染回复
            reply_list = comment.get("reply_list", [])
            if reply_list:
                html += '<div class="reply-list">\n'
                for reply in reply_list:
                    reply_nick = reply.get("nick_name", "匿名用户")
                    reply_content = reply.get("content", "")
                    html += f'<div class="reply-item"><strong>{reply_nick}</strong>：{reply_content}</div>\n'
                html += '</div>\n'
            
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        safe_name = re.sub(illegal_chars, '_', filename)
        
        # 限制长度
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name.strip()
    
    async def export_article_markdown(
        self,
        html_content: str,
        article_info: Dict,
        include_images: bool = True,
        timeout: int = 30
    ) -> str:
        """
        导出文章为Markdown格式
        
        Args:
            html_content: 文章HTML内容
            article_info: 文章信息
            include_images: 是否包含图片（下载到本地）
            timeout: 下载超时时间
            
        Returns:
            导出文件路径
        """
        article_id = article_info.get("article_id", "unknown")
        title = article_info.get("title", "未知标题")
        fakeid = article_info.get("fakeid", "")
        
        safe_title = self._sanitize_filename(title)
        
        # 创建导出目录
        if fakeid:
            export_dir = self.base_export_path / fakeid
        else:
            export_dir = self.base_export_path
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取文章内容区域
        js_content = soup.find(id='js_content')
        if not js_content:
            js_content = soup.find('div', class_='rich_media_content')
        if not js_content:
            js_content = soup
        
        # 下载图片（如果需要）
        url_map: Dict[str, str] = {}
        if include_images:
            images_dir = export_dir / f"{safe_title}_images"
            images_dir.mkdir(exist_ok=True)
            
            for idx, img in enumerate(js_content.find_all('img')):
                img_url = img.get('data-src') or img.get('src')
                if img_url and not img_url.startswith('data:'):
                    local_path = await self._download_resource(img_url, images_dir, f"img_{idx}", timeout)
                    if local_path:
                        url_map[img_url] = f"./{safe_title}_images/{local_path.name}"
        
        # 转换为Markdown
        markdown_content = self._html_to_markdown(js_content, url_map)
        
        # 添加标题和元信息
        create_time = article_info.get("create_time", 0)
        author = article_info.get("author", "")
        account_name = article_info.get("account_name", "")
        
        header = f"# {title}\n\n"
        if author or account_name:
            header += f"> 作者：{author or account_name}\n"
        if create_time:
            from datetime import datetime
            dt = datetime.fromtimestamp(create_time)
            header += f"> 发布时间：{dt.strftime('%Y-%m-%d %H:%M')}\n"
        header += "\n---\n\n"
        
        full_content = header + markdown_content
        
        # 写入文件
        md_file = export_dir / f"{safe_title}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        utils.logger.info(f"[WeChatArticleExporter] Markdown exported to: {md_file}")
        
        return str(md_file)
    
    def _html_to_markdown(self, element, url_map: Dict[str, str]) -> str:
        """将HTML元素转换为Markdown"""
        lines = []
        
        def process_element(elem, depth=0):
            if elem.name is None:  # 文本节点
                text = str(elem).strip()
                if text:
                    lines.append(text)
                return
            
            tag = elem.name.lower()
            
            if tag in ['script', 'style', 'noscript']:
                return
            
            if tag == 'h1':
                lines.append(f"\n# {elem.get_text(strip=True)}\n")
            elif tag == 'h2':
                lines.append(f"\n## {elem.get_text(strip=True)}\n")
            elif tag == 'h3':
                lines.append(f"\n### {elem.get_text(strip=True)}\n")
            elif tag == 'h4':
                lines.append(f"\n#### {elem.get_text(strip=True)}\n")
            elif tag == 'p':
                text = elem.get_text(strip=True)
                if text:
                    lines.append(f"\n{text}\n")
            elif tag == 'br':
                lines.append("\n")
            elif tag == 'strong' or tag == 'b':
                text = elem.get_text(strip=True)
                if text:
                    lines.append(f"**{text}**")
            elif tag == 'em' or tag == 'i':
                text = elem.get_text(strip=True)
                if text:
                    lines.append(f"*{text}*")
            elif tag == 'a':
                href = elem.get('href', '')
                text = elem.get_text(strip=True)
                if href and text:
                    lines.append(f"[{text}]({href})")
                elif text:
                    lines.append(text)
            elif tag == 'img':
                src = elem.get('data-src') or elem.get('src', '')
                alt = elem.get('alt', 'image')
                if src:
                    # 使用本地路径（如果有）
                    local_src = url_map.get(src, src)
                    lines.append(f"\n![{alt}]({local_src})\n")
            elif tag == 'ul':
                lines.append("\n")
                for li in elem.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        lines.append(f"- {text}\n")
            elif tag == 'ol':
                lines.append("\n")
                for idx, li in enumerate(elem.find_all('li', recursive=False), 1):
                    text = li.get_text(strip=True)
                    if text:
                        lines.append(f"{idx}. {text}\n")
            elif tag == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    quoted = '\n'.join([f"> {line}" for line in text.split('\n')])
                    lines.append(f"\n{quoted}\n")
            elif tag == 'pre' or tag == 'code':
                code = elem.get_text()
                if tag == 'pre':
                    lines.append(f"\n```\n{code}\n```\n")
                else:
                    lines.append(f"`{code}`")
            elif tag == 'hr':
                lines.append("\n---\n")
            elif tag == 'section' or tag == 'div' or tag == 'span':
                # 递归处理子元素
                for child in elem.children:
                    process_element(child, depth + 1)
            else:
                # 其他标签，只提取文本
                text = elem.get_text(strip=True)
                if text and len(text) > 0:
                    lines.append(text)
        
        process_element(element)
        
        # 清理结果
        result = ''.join(lines)
        # 移除多余的空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    async def export_article_txt(
        self,
        html_content: str,
        article_info: Dict
    ) -> str:
        """
        导出文章为纯文本格式
        
        Args:
            html_content: 文章HTML内容
            article_info: 文章信息
            
        Returns:
            导出文件路径
        """
        article_id = article_info.get("article_id", "unknown")
        title = article_info.get("title", "未知标题")
        fakeid = article_info.get("fakeid", "")
        
        safe_title = self._sanitize_filename(title)
        
        # 创建导出目录
        if fakeid:
            export_dir = self.base_export_path / fakeid
        else:
            export_dir = self.base_export_path
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取文章内容区域
        js_content = soup.find(id='js_content')
        if not js_content:
            js_content = soup.find('div', class_='rich_media_content')
        if not js_content:
            js_content = soup
        
        # 移除脚本和样式
        for tag in js_content.find_all(['script', 'style']):
            tag.decompose()
        
        # 提取纯文本
        text_content = js_content.get_text(separator='\n', strip=True)
        
        # 清理多余空行
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)
        
        # 添加标题
        header = f"{title}\n{'=' * len(title)}\n\n"
        
        create_time = article_info.get("create_time", 0)
        author = article_info.get("author", "")
        account_name = article_info.get("account_name", "")
        
        if author or account_name:
            header += f"作者：{author or account_name}\n"
        if create_time:
            from datetime import datetime
            dt = datetime.fromtimestamp(create_time)
            header += f"发布时间：{dt.strftime('%Y-%m-%d %H:%M')}\n"
        header += "\n" + "-" * 40 + "\n\n"
        
        full_content = header + text_content
        
        # 写入文件
        txt_file = export_dir / f"{safe_title}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        utils.logger.info(f"[WeChatArticleExporter] TXT exported to: {txt_file}")
        
        return str(txt_file)
    
    async def export_article_docx(
        self,
        html_content: str,
        article_info: Dict,
        include_images: bool = True,
        timeout: int = 30
    ) -> Optional[str]:
        """
        导出文章为Word文档（DOCX格式）
        
        需要安装 python-docx 库
        
        Args:
            html_content: 文章HTML内容
            article_info: 文章信息
            include_images: 是否包含图片
            timeout: 下载超时时间
            
        Returns:
            导出文件路径，如果失败返回None
        """
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            utils.logger.error("[WeChatArticleExporter] python-docx not installed. Run: pip install python-docx")
            return None
        
        article_id = article_info.get("article_id", "unknown")
        title = article_info.get("title", "未知标题")
        fakeid = article_info.get("fakeid", "")
        
        safe_title = self._sanitize_filename(title)
        
        # 创建导出目录
        if fakeid:
            export_dir = self.base_export_path / fakeid
        else:
            export_dir = self.base_export_path
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 获取文章内容区域
        js_content = soup.find(id='js_content')
        if not js_content:
            js_content = soup.find('div', class_='rich_media_content')
        if not js_content:
            js_content = soup
        
        # 创建Word文档
        doc = Document()
        
        # 添加标题
        title_para = doc.add_heading(title, level=0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 添加元信息
        create_time = article_info.get("create_time", 0)
        author = article_info.get("author", "")
        account_name = article_info.get("account_name", "")
        
        meta_parts = []
        if author or account_name:
            meta_parts.append(f"作者：{author or account_name}")
        if create_time:
            from datetime import datetime
            dt = datetime.fromtimestamp(create_time)
            meta_parts.append(f"发布时间：{dt.strftime('%Y-%m-%d %H:%M')}")
        
        if meta_parts:
            meta_para = doc.add_paragraph(' | '.join(meta_parts))
            meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()  # 空行
        
        # 下载图片（如果需要）
        temp_images: List[Path] = []
        if include_images:
            temp_dir = export_dir / ".temp_images"
            temp_dir.mkdir(exist_ok=True)
            
            for idx, img in enumerate(js_content.find_all('img')):
                img_url = img.get('data-src') or img.get('src')
                if img_url and not img_url.startswith('data:'):
                    local_path = await self._download_resource(img_url, temp_dir, f"img_{idx}", timeout)
                    if local_path:
                        img['local_path'] = str(local_path)
                        temp_images.append(local_path)
        
        # 转换HTML到Word
        self._html_to_docx(js_content, doc, include_images)
        
        # 保存文档
        docx_file = export_dir / f"{safe_title}.docx"
        doc.save(str(docx_file))
        
        # 清理临时图片
        if temp_images:
            import shutil
            temp_dir = export_dir / ".temp_images"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        utils.logger.info(f"[WeChatArticleExporter] DOCX exported to: {docx_file}")
        
        return str(docx_file)
    
    def _html_to_docx(self, element, doc, include_images: bool):
        """将HTML元素转换为Word文档内容"""
        try:
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            return
        
        def process_element(elem):
            if elem.name is None:  # 文本节点
                return
            
            tag = elem.name.lower()
            
            if tag in ['script', 'style', 'noscript']:
                return
            
            if tag in ['h1', 'h2', 'h3', 'h4']:
                level = int(tag[1])
                doc.add_heading(elem.get_text(strip=True), level=level)
            elif tag == 'p':
                text = elem.get_text(strip=True)
                if text:
                    doc.add_paragraph(text)
            elif tag == 'img' and include_images:
                local_path = elem.get('local_path')
                if local_path and Path(local_path).exists():
                    try:
                        doc.add_picture(local_path, width=Inches(5.5))
                    except Exception as e:
                        utils.logger.warning(f"Failed to add image: {e}")
            elif tag == 'ul':
                for li in elem.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        doc.add_paragraph(text, style='List Bullet')
            elif tag == 'ol':
                for li in elem.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        doc.add_paragraph(text, style='List Number')
            elif tag == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    para = doc.add_paragraph(text)
                    para.style = 'Quote'
            elif tag in ['section', 'div', 'span', 'article']:
                for child in elem.children:
                    process_element(child)
        
        for child in element.children:
            process_element(child)


# 便捷函数
async def export_to_html(html_content: str, article_info: Dict, **kwargs) -> Tuple[str, Dict]:
    """导出为HTML格式"""
    exporter = WeChatArticleExporter()
    return await exporter.export_article_html(html_content, article_info, **kwargs)


async def export_to_markdown(html_content: str, article_info: Dict, **kwargs) -> str:
    """导出为Markdown格式"""
    exporter = WeChatArticleExporter()
    return await exporter.export_article_markdown(html_content, article_info, **kwargs)


async def export_to_txt(html_content: str, article_info: Dict) -> str:
    """导出为TXT格式"""
    exporter = WeChatArticleExporter()
    return await exporter.export_article_txt(html_content, article_info)


async def export_to_docx(html_content: str, article_info: Dict, **kwargs) -> Optional[str]:
    """导出为DOCX格式"""
    exporter = WeChatArticleExporter()
    return await exporter.export_article_docx(html_content, article_info, **kwargs)

