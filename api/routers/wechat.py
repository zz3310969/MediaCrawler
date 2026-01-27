import httpx
import re
import html
import hashlib
import asyncio
from urllib.parse import quote, urlparse, urljoin
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import zipfile
from tools import utils

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    utils.logger.warning("[WeChatAPI] BeautifulSoup not installed, HTML export may be limited")

router = APIRouter(prefix="/wechat", tags=["wechat"])


# ==================== 请求/响应模型 ====================

class WeChatSearchRequest(BaseModel):
    keyword: str
    cookies: str
    token: str
    begin: int = 0
    count: int = 5


class ArticleItem(BaseModel):
    """文章列表项"""
    id: int
    article_id: str
    title: str
    account_name: str
    read_num: int
    like_num: int
    comment_count: int
    create_time: int
    link: str
    cover: Optional[str] = None


class ArticleListResponse(BaseModel):
    """文章列表响应"""
    articles: List[ArticleItem]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """统计数据响应"""
    total_articles: int
    total_reads: int
    total_likes: int
    total_accounts: int
    today_articles: int
    today_reads: int


class TopArticleItem(BaseModel):
    """热门文章项"""
    id: int
    title: str
    account_name: str
    read_num: int
    create_time: int


class AccountItem(BaseModel):
    """公众号列表项"""
    fakeid: str
    account_name: str
    article_count: int


class ExportRequest(BaseModel):
    """导出请求"""
    article_ids: List[int]
    format: str = "html"  # html, markdown, json


class RefetchRequest(BaseModel):
    """重新采集请求"""
    article_ids: List[int]


class RefetchResult(BaseModel):
    """重新采集结果"""
    success: int
    failed: int
    results: List[dict]


class ArticleExportItem(BaseModel):
    """导出的文章详情"""
    id: int
    article_id: str
    title: str
    account_name: str
    author: str
    content: str
    create_time: int
    link: str
    read_num: int
    like_num: int
    comment_count: int


def html_to_markdown(html_content: str, title: str = "") -> str:
    """将 HTML 转换为 Markdown（简化版）"""
    if not html_content:
        return ""
    
    text = html_content
    
    # 移除 script 和 style 标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换标题
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换段落和换行
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换粗体和斜体
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换链接
    text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换图片
    text = re.sub(r'<img[^>]*data-src=["\']([^"\']*)["\'][^>]*/?>', r'![](\1)\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>', r'![](\1)\n', text, flags=re.IGNORECASE)
    
    # 转换列表
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'</?[ou]l[^>]*>', '', text, flags=re.IGNORECASE)
    
    # 转换代码块
    text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 转换引用
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '> ' + m.group(1).replace('\n', '\n> ') + '\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除剩余的 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 解码 HTML 实体
    text = html.unescape(text)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    # 添加标题
    if title:
        text = f"# {title}\n\n{text}"
    
    return text


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    return name or "untitled"


def extract_resources_from_html(html_content: str) -> Set[str]:
    """从 HTML 中提取所有需要下载的资源（图片、CSS）"""
    resources = set()
    
    # 提取图片 src
    src_pattern = r'<img[^>]*\bsrc=["\']([^"\']+)["\']'
    for match in re.finditer(src_pattern, html_content, re.IGNORECASE):
        url = match.group(1)
        if url and (url.startswith('http') or url.startswith('//')):
            if url.startswith('//'):
                url = 'https:' + url
            resources.add(url)
    
    # 提取图片 data-src（单独提取，确保不遗漏）
    data_src_pattern = r'<img[^>]*\bdata-src=["\']([^"\']+)["\']'
    for match in re.finditer(data_src_pattern, html_content, re.IGNORECASE):
        url = match.group(1)
        if url and (url.startswith('http') or url.startswith('//')):
            if url.startswith('//'):
                url = 'https:' + url
            resources.add(url)
    
    # 提取 CSS 链接 - 使用更宽松的正则，因为 link 标签属性顺序不固定
    # 匹配所有 <link> 标签中的 href
    link_pattern = r'<link[^>]*href=["\']([^"\']+)["\'][^>]*>'
    for match in re.finditer(link_pattern, html_content, re.IGNORECASE):
        tag = match.group(0)
        href = match.group(1)
        # 只处理 stylesheet 链接
        if 'stylesheet' in tag.lower() and href:
            url = href
            if url.startswith('//'):
                url = 'https:' + url
            if url.startswith('http'):
                resources.add(url)
    
    # 提取背景图片 url()
    bg_pattern = r'(?:background|background-image)\s*:\s*url\(["\']?([^"\')\s]+)["\']?\)'
    for match in re.finditer(bg_pattern, html_content, re.IGNORECASE):
        url = match.group(1)
        if url and (url.startswith('http') or url.startswith('//')):
            if url.startswith('//'):
                url = 'https:' + url
            resources.add(url)
    
    # 提取背景图片 url() - 处理 &quot; 转义的情况（参考 wechat-article-exporter）
    bg_pattern_escaped = r'(?:background|background-image)\s*:\s*url\(&quot;((?:https?|//)[^&]+)&quot;\)'
    for match in re.finditer(bg_pattern_escaped, html_content, re.IGNORECASE):
        url = match.group(1)
        if url:
            if url.startswith('//'):
                url = 'https:' + url
            resources.add(url)
    
    return resources


def get_url_hash(url: str) -> str:
    """生成 URL 的短哈希作为文件名"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def get_extension_from_url(url: str, content_type: str = '') -> str:
    """从 URL 或 Content-Type 获取文件扩展名"""
    # 从 Content-Type 获取
    if content_type:
        if 'css' in content_type:
            return '.css'
        elif 'png' in content_type:
            return '.png'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        elif 'svg' in content_type:
            return '.svg'
    
    # 从 URL 路径获取
    parsed = urlparse(url)
    path = parsed.path.lower()
    if '.css' in path:
        return '.css'
    elif '.png' in path:
        return '.png'
    elif '.jpg' in path or '.jpeg' in path:
        return '.jpg'
    elif '.gif' in path:
        return '.gif'
    elif '.webp' in path:
        return '.webp'
    elif '.svg' in path:
        return '.svg'
    
    # 默认为图片
    return '.jpg'


async def download_resource(url: str, timeout: float = 15.0) -> Tuple[Optional[bytes], str]:
    """下载单个资源，返回 (内容, content_type)"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Referer": "https://mp.weixin.qq.com/",
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                return response.content, content_type
    except Exception as e:
        utils.logger.warning(f"[WeChatAPI] Failed to download resource: {url}, error: {e}")
    return None, ''


def replace_resources_in_html(html_content: str, url_map: Dict[str, str]) -> str:
    """替换 HTML 中的资源 URL 为本地路径"""
    result = html_content
    
    for original_url, local_path in url_map.items():
        # 替换各种形式的 URL 引用
        # 处理 // 开头的 URL
        if original_url.startswith('https://'):
            no_protocol = original_url.replace('https:', '')
            result = result.replace(f'"{no_protocol}"', f'"{local_path}"')
            result = result.replace(f"'{no_protocol}'", f"'{local_path}'")
        
        # 替换完整 URL
        result = result.replace(f'"{original_url}"', f'"{local_path}"')
        result = result.replace(f"'{original_url}'", f"'{local_path}'")
        
        # 替换 url() 中的引用（包括 &quot; 转义的情况）
        result = result.replace(f'url({original_url})', f'url({local_path})')
        result = result.replace(f'url("{original_url}")', f'url("{local_path}")')
        result = result.replace(f"url('{original_url}')", f"url('{local_path}')")
        result = result.replace(f'url(&quot;{original_url}&quot;)', f'url(&quot;{local_path}&quot;)')
    
    # 关键：处理图片的 data-src -> src 转换
    # 参考 wechat-article-exporter：img.src = img.getAttribute('src') || img.getAttribute('data-src')
    # 最简单直接的方法：将 data-src 改名为 src
    # 但要注意不要影响已有的 src 属性
    
    # 方法：对于每个 img 标签，如果没有 src 属性，将 data-src 改为 src
    def fix_img_src(match):
        img_tag = match.group(0)
        # 检查是否已经有 src 属性（使用 \bsrc= 确保不匹配 data-src）
        has_src = re.search(r'(?<![a-zA-Z-])src=["\']', img_tag)
        if has_src:
            # 已经有 src，不需要处理
            return img_tag
        # 没有 src，将 data-src 改为 src
        return re.sub(r'\bdata-src=', 'src=', img_tag)
    
    # 匹配所有 img 标签
    result = re.sub(r'<img\s[^>]*>', fix_img_src, result, flags=re.IGNORECASE)
    
    return result


def clean_html_for_export(html_content: str, url_map: Dict[str, str]) -> Tuple[str, str, List[str]]:
    """
    按照 wechat-article-exporter 的方式清理 HTML
    
    关键：只提取 #js_article 的内容，完全丢弃外层的 HTML 结构
    
    返回: (page_content_html, body_class, css_links)
    """
    if not HAS_BS4:
        # 降级处理：简单的正则清理
        return _clean_html_regex_fallback(html_content, url_map)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 获取 body class（用于保持微信原有样式）- 在删除任何内容之前获取
    body = soup.find('body')
    body_class = body.get('class', []) if body else []
    body_class_str = ' '.join(body_class) if isinstance(body_class, list) else str(body_class)
    utils.logger.debug(f"[WeChatAPI] Extracted body class: {body_class_str[:100]}...")
    
    # 提取 CSS 链接（只包含已下载的本地 CSS）- 在删除 head 之前提取
    css_links = []
    
    # 方法1：从 HTML 中的 link 标签提取
    for link in soup.find_all('link'):
        # 检查是否是 stylesheet
        rel = link.get('rel', [])
        if isinstance(rel, list):
            rel = ' '.join(rel)
        if 'stylesheet' not in str(rel).lower():
            continue
            
        href = link.get('href', '')
        if href:
            original_href = href
            # 尝试多种 URL 格式
            urls_to_try = [href]
            if href.startswith('//'):
                urls_to_try.append('https:' + href)
                urls_to_try.append('http:' + href)
            elif href.startswith('https://'):
                urls_to_try.append('//' + href[8:])
            elif href.startswith('http://'):
                urls_to_try.append('//' + href[7:])
            
            for url in urls_to_try:
                if url in url_map:
                    css_links.append(url_map[url])
                    utils.logger.debug(f"[WeChatAPI] CSS link mapped: {original_href} -> {url_map[url]}")
                    break
            else:
                utils.logger.debug(f"[WeChatAPI] CSS link not in url_map: {href}")
    
    # 方法2：如果从 HTML 中提取的 CSS 链接为空，直接从 url_map 中获取所有 CSS 文件
    if not css_links:
        utils.logger.info("[WeChatAPI] No CSS links found from HTML, getting from url_map directly")
        for url, local_path in url_map.items():
            if local_path.endswith('.css'):
                css_links.append(local_path)
                utils.logger.debug(f"[WeChatAPI] CSS from url_map: {url} -> {local_path}")
    
    utils.logger.info(f"[WeChatAPI] Found {len(css_links)} CSS links")
    
    # ===== 查找主内容区域 #js_article =====
    js_article = soup.find(id='js_article')
    if not js_article:
        # 如果没有 #js_article，尝试找 #js_content
        js_article = soup.find(id='js_content')
    if not js_article:
        # 还是没有，尝试找 body 里的内容
        js_article = body if body else soup
    
    # ===== 在 js_article 内部删除所有不需要的标签 =====
    # 删除所有 script 标签
    for script in js_article.find_all('script'):
        script.decompose()
    # 删除所有 noscript 标签
    for noscript in js_article.find_all('noscript'):
        noscript.decompose()
    # 删除所有 link 标签（JS模块预加载、dns-prefetch等）
    for link in js_article.find_all('link'):
        link.decompose()
    # 删除所有 style 标签（内联样式块）
    # 注意：保留 style 属性，只删除 <style> 标签
    for style_tag in js_article.find_all('style'):
        style_tag.decompose()
    
    # 删除无用 DOM 元素（参考 wechat-article-exporter）
    elements_to_remove = [
        '#js_top_ad_area',           # 顶部广告
        '#js_tags_preview_toast',    # 标签提示
        '#content_bottom_area',      # 底部区域
        '#js_pc_qr_code',            # PC二维码
        '#wx_stream_article_slide_tip',  # 滑动提示
        '#js_temp_bottom_area',      # 临时底部区域
        '#js_profile_card',          # 公众号名片
        '.weui-dialog__wrp',         # 对话框
        '.outer_dialog',             # 外部对话框
        '#js_alert_panel',           # 提示面板
        '#js_link_dialog',           # 链接对话框
        '#js_minipro_dialog',        # 小程序对话框
        '#js_product_dialog',        # 商品对话框
        '#js_pc_weapp_code',         # PC小程序码
        '#js_analyze_btn',           # 分析按钮
        '.jump_wx_qrcode_dialog',    # 跳转二维码对话框
        '#unlogin_bottom_bar',       # 未登录底部栏
        '.weui-a11y_ref',            # 无障碍引用
        '#js_emotion_panel_pc',      # 表情面板
        '#js_profile_card_modal',    # 名片模态框
        '#audio_panel_area',         # 音频面板
        '#js_ad_control',            # 广告控制
        '#wx_expand_article',        # 展开文章
        '.wx_network_msg_wrp',       # 网络消息
    ]
    for selector in elements_to_remove:
        for el in js_article.select(selector):
            el.decompose()
    
    # 处理 #js_content 的可见性（移除 visibility: hidden 和 opacity: 0）
    js_content = js_article.find(id='js_content')
    if js_content and js_content.has_attr('style'):
        style = js_content['style']
        # 移除 visibility: hidden
        style = re.sub(r'visibility\s*:\s*hidden\s*;?', '', style, flags=re.IGNORECASE)
        # 移除 opacity: 0
        style = re.sub(r'opacity\s*:\s*0\s*;?', '', style, flags=re.IGNORECASE)
        if style.strip():
            js_content['style'] = style
        else:
            del js_content['style']
    
    # 处理图片懒加载：参考 wechat-article-exporter 的做法
    # 关键：设置 img.src 属性，这样浏览器才会加载图片
    for img in js_article.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')
        
        # 获取图片的原始 URL（优先使用 src，然后是 data-src）
        # wechat-article-exporter: const url = img.getAttribute('src') || img.getAttribute('data-src');
        img_url = src or data_src
        
        if img_url:
            # 尝试多种 URL 格式来查找本地路径映射
            local_path = None
            urls_to_try = [img_url]
            
            # 处理 // 开头的 URL
            if img_url.startswith('//'):
                urls_to_try.append('https:' + img_url)
                urls_to_try.append('http:' + img_url)
            elif img_url.startswith('https://'):
                urls_to_try.append('//' + img_url[8:])  # 去掉 https:
            elif img_url.startswith('http://'):
                urls_to_try.append('//' + img_url[7:])  # 去掉 http:
            
            # 尝试所有可能的 URL 格式
            for url in urls_to_try:
                if url in url_map:
                    local_path = url_map[url]
                    break
            
            if local_path:
                # 设置 src 为本地路径（关键！）
                img['src'] = local_path
                # 删除 data-src 属性（参考 wechat-article-exporter，它只设置 src）
                if img.has_attr('data-src'):
                    del img['data-src']
            elif data_src:
                # 没有本地映射，但有 data-src，复制到 src
                # 这样浏览器至少可以尝试加载原始 URL
                img['src'] = data_src
                # 删除 data-src，因为已经复制到 src 了
                if img.has_attr('data-src'):
                    del img['data-src']
    
    # ===== 获取最终的内容 HTML（只取 js_article 的内部内容）=====
    # 使用 decode_contents() 只获取内部内容，不包含外层标签
    # 但我们需要保留 #js_article 本身，所以用 str()
    page_content_html = str(js_article)
    
    # ===== 彻底清理：用正则移除所有不应该出现在 body 中的内容 =====
    # 这是最关键的步骤！
    
    # 1. 移除所有 script 标签（包括各种格式）
    page_content_html = re.sub(r'<script[^>]*>.*?</script>', '', page_content_html, flags=re.DOTALL | re.IGNORECASE)
    page_content_html = re.sub(r'<script[^>]*/>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'<script[^>]*>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'</script>', '', page_content_html, flags=re.IGNORECASE)
    
    # 2. 移除所有 noscript 标签
    page_content_html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', page_content_html, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. 移除所有 link 标签（modulepreload, dns-prefetch, preconnect, stylesheet 等）
    page_content_html = re.sub(r'<link[^>]*/?>', '', page_content_html, flags=re.IGNORECASE)
    
    # 4. 移除所有 meta 标签（不应该出现在 body 中）
    page_content_html = re.sub(r'<meta[^>]*/?>', '', page_content_html, flags=re.IGNORECASE)
    
    # 5. 移除任何嵌套的 HTML 结构（最关键！）
    page_content_html = re.sub(r'<!DOCTYPE[^>]*>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'<html[^>]*>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'</html>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'<head[^>]*>.*?</head>', '', page_content_html, flags=re.DOTALL | re.IGNORECASE)
    page_content_html = re.sub(r'<body[^>]*>', '', page_content_html, flags=re.IGNORECASE)
    page_content_html = re.sub(r'</body>', '', page_content_html, flags=re.IGNORECASE)
    
    # 6. 移除 title 标签
    page_content_html = re.sub(r'<title[^>]*>.*?</title>', '', page_content_html, flags=re.DOTALL | re.IGNORECASE)
    
    # 7. 移除 style 标签（内联样式块，CSS 已经通过 css_links 处理）
    page_content_html = re.sub(r'<style[^>]*>.*?</style>', '', page_content_html, flags=re.DOTALL | re.IGNORECASE)
    
    # 替换背景图片 URL（用正则处理，因为可能在 style 属性中）
    page_content_html = replace_resources_in_html(page_content_html, url_map)
    
    return page_content_html, body_class_str, css_links


def _clean_html_regex_fallback(html_content: str, url_map: Dict[str, str]) -> Tuple[str, str, List[str]]:
    """
    降级处理：使用正则清理 HTML（当 BeautifulSoup 不可用时）
    
    注意：这个函数只在 BeautifulSoup 不可用时使用，清理效果不如 BeautifulSoup 版本
    """
    result = html_content
    
    # 尝试提取 #js_article 的内容
    js_article_match = re.search(r'(<div[^>]*id=["\']js_article["\'][^>]*>.*)', result, flags=re.DOTALL | re.IGNORECASE)
    if js_article_match:
        result = js_article_match.group(1)
    
    # ===== 彻底移除所有 script 标签 =====
    result = re.sub(r'<script[^>]*>.*?</script>', '', result, flags=re.DOTALL | re.IGNORECASE)
    result = re.sub(r'<script[^>]*/>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'<script[^>]*>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'</script>', '', result, flags=re.IGNORECASE)
    
    # 移除 noscript 标签
    result = re.sub(r'<noscript[^>]*>.*?</noscript>', '', result, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除所有 link 标签
    result = re.sub(r'<link[^>]*/?>', '', result, flags=re.IGNORECASE)
    
    # 移除所有 meta 标签
    result = re.sub(r'<meta[^>]*/?>', '', result, flags=re.IGNORECASE)
    
    # 移除所有 style 标签
    result = re.sub(r'<style[^>]*>.*?</style>', '', result, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除 HTML 结构标签
    result = re.sub(r'<!DOCTYPE[^>]*>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'<html[^>]*>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'</html>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'<head[^>]*>.*?</head>', '', result, flags=re.DOTALL | re.IGNORECASE)
    result = re.sub(r'<body[^>]*>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'</body>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'<title[^>]*>.*?</title>', '', result, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除一些不需要的元素
    patterns_to_remove = [
        r'<[^>]*id=["\']js_top_ad_area["\'][^>]*>.*?</[^>]+>',
        r'<[^>]*id=["\']js_tags_preview_toast["\'][^>]*>.*?</[^>]+>',
        r'<[^>]*id=["\']js_pc_qr_code["\'][^>]*>.*?</[^>]+>',
        r'<[^>]*id=["\']content_bottom_area["\'][^>]*>.*?</[^>]+>',
    ]
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.DOTALL | re.IGNORECASE)
    
    # 将 data-src 复制到 src（懒加载图片）
    def replace_data_src(match):
        tag = match.group(0)
        src_match = re.search(r'\bsrc=["\']([^"\']*)["\']', tag, re.IGNORECASE)
        data_src_match = re.search(r'data-src=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if data_src_match:
            data_src = data_src_match.group(1)
            if not src_match or not src_match.group(1) or 'data:image' in src_match.group(1):
                if src_match:
                    tag = re.sub(r'\bsrc=["\'][^"\']*["\']', f'src="{data_src}"', tag, flags=re.IGNORECASE)
                else:
                    tag = tag.replace('data-src=', 'src=')
        return tag
    
    result = re.sub(r'<img[^>]+>', replace_data_src, result, flags=re.IGNORECASE)
    
    # 移除 #js_content 的 visibility: hidden 和 opacity: 0 样式
    result = re.sub(
        r'(id=["\']js_content["\'][^>]*style=["\'][^"\']*)(visibility:\s*hidden;?)',
        r'\1',
        result,
        flags=re.IGNORECASE
    )
    result = re.sub(
        r'(id=["\']js_content["\'][^>]*style=["\'][^"\']*)(opacity:\s*0;?)',
        r'\1',
        result,
        flags=re.IGNORECASE
    )
    
    # 替换资源 URL
    result = replace_resources_in_html(result, url_map)
    
    # 从 url_map 中获取所有 CSS 文件
    css_links = [local_path for url, local_path in url_map.items() if local_path.endswith('.css')]
    utils.logger.info(f"[WeChatAPI] Regex fallback: Found {len(css_links)} CSS files from url_map")
    
    return result, '', css_links


def generate_final_html(title: str, page_content: str, body_class: str, css_links: List[str]) -> str:
    """
    生成最终的 HTML 文档（参考 wechat-article-exporter 的格式）
    """
    # 构建本地 CSS 链接
    local_css = '\n'.join([f'    <link rel="stylesheet" href="{link}">' for link in css_links])
    
    return f'''<!DOCTYPE html>
<html lang="zh_CN">
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=0,viewport-fit=cover">
    <title>{html.escape(title)}</title>
{local_css}
    <style>
        #page-content,
        #js_article,
        #js_article_bottom_bar,
        .__page_content__ {{
            max-width: 677px;
            margin: 0 auto;
        }}
        #js_content {{
            visibility: visible !important;
        }}
        .rich_media_content {{
            overflow: visible !important;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }}
    </style>
</head>
<body class="{body_class}">
{page_content}
</body>
</html>'''


@router.get("/accounts", response_model=List[AccountItem])
async def get_accounts():
    """
    获取所有已采集的公众号列表（去重）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, distinct
        
        async with get_session() as session:
            # 获取所有公众号及其文章数量
            query = select(
                WeChatArticle.fakeid,
                WeChatArticle.account_name,
                func.count(WeChatArticle.id).label('article_count')
            ).group_by(
                WeChatArticle.fakeid,
                WeChatArticle.account_name
            ).order_by(
                func.count(WeChatArticle.id).desc()
            )
            
            result = await session.execute(query)
            accounts = result.all()
            
            return [
                AccountItem(
                    fakeid=row.fakeid or "",
                    account_name=row.account_name or "未知公众号",
                    article_count=row.article_count or 0,
                )
                for row in accounts
                if row.fakeid  # 过滤掉空的 fakeid
            ]
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get accounts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_account")
async def search_account(request: WeChatSearchRequest):
    """
    搜索公众号
    """
    if not request.token:
        raise HTTPException(status_code=400, detail="Token is required")

    uri = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
    params = {
        "action": "search_biz",
        "begin": request.begin,
        "count": request.count,
        "query": request.keyword,
        "token": request.token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": request.cookies,
        "Referer": f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&token={request.token}&lang=zh_CN"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(uri, params=params, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="HTTP error from WeChat")

            try:
                data = response.json()
            except Exception:
                 raise HTTPException(status_code=500, detail="Invalid JSON response from WeChat")
            
            # Check for errors
            base_resp = data.get("base_resp", {})
            ret = base_resp.get("ret")
            if ret != 0:
                err_msg = base_resp.get("err_msg", "Unknown error")
                if ret == 200003:
                    raise HTTPException(status_code=429, detail="Rate limited (freq control)")
                if ret == 200013:
                     raise HTTPException(status_code=401, detail="Session expired")
                raise HTTPException(status_code=400, detail=f"WeChat API error ({ret}): {err_msg}")
                
            return data
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据查询 API ====================

@router.get("/articles", response_model=ArticleListResponse)
async def get_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索标题"),
    time_range: Optional[str] = Query(None, description="时间范围: today, week, month, all"),
    order_by: Optional[str] = Query("create_time", description="排序字段: create_time, read_num, like_num"),
    order_dir: Optional[str] = Query("desc", description="排序方向: asc, desc"),
    account_ids: Optional[str] = Query(None, description="公众号ID列表，逗号分隔"),
):
    """
    获取微信文章列表（分页）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, desc, asc
        
        async with get_session() as session:
            # 构建基础查询
            query = select(WeChatArticle)
            count_query = select(func.count(WeChatArticle.id))
            
            # 公众号过滤
            if account_ids:
                fakeid_list = [fid.strip() for fid in account_ids.split(",") if fid.strip()]
                if fakeid_list:
                    account_filter = WeChatArticle.fakeid.in_(fakeid_list)
                    query = query.where(account_filter)
                    count_query = count_query.where(account_filter)
            
            # 搜索条件
            if search:
                search_filter = WeChatArticle.title.ilike(f"%{search}%")
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)
            
            # 时间范围过滤
            if time_range and time_range != "all":
                now = datetime.now()
                if time_range == "today":
                    start_ts = int(datetime(now.year, now.month, now.day).timestamp())
                elif time_range == "week":
                    start_ts = int((now - timedelta(days=7)).timestamp())
                elif time_range == "month":
                    start_ts = int((now - timedelta(days=30)).timestamp())
                else:
                    start_ts = None
                
                if start_ts:
                    time_filter = WeChatArticle.create_time >= start_ts
                    query = query.where(time_filter)
                    count_query = count_query.where(time_filter)
            
            # 排序
            order_column = getattr(WeChatArticle, order_by, WeChatArticle.create_time)
            if order_dir == "asc":
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))
            
            # 获取总数
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0
            
            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # 执行查询
            result = await session.execute(query)
            articles = result.scalars().all()
            
            # 转换为响应格式
            article_list = [
                ArticleItem(
                    id=article.id,
                    article_id=article.article_id,
                    title=article.title or "",
                    account_name=article.account_name or "",
                    read_num=article.read_num or 0,
                    like_num=article.like_num or 0,
                    comment_count=article.comment_count or 0,
                    create_time=article.create_time or 0,
                    link=article.link or "",
                    cover=article.cover,
                )
                for article in articles
            ]
            
            return ArticleListResponse(
                articles=article_list,
                total=total,
                page=page,
                page_size=page_size,
            )
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    获取微信数据统计
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, func, distinct
        
        async with get_session() as session:
            # 文章总数
            total_articles_result = await session.execute(
                select(func.count(WeChatArticle.id))
            )
            total_articles = total_articles_result.scalar() or 0
            
            # 总阅读量
            total_reads_result = await session.execute(
                select(func.sum(WeChatArticle.read_num))
            )
            total_reads = total_reads_result.scalar() or 0
            
            # 总点赞数
            total_likes_result = await session.execute(
                select(func.sum(WeChatArticle.like_num))
            )
            total_likes = total_likes_result.scalar() or 0
            
            # 公众号数量（去重）
            total_accounts_result = await session.execute(
                select(func.count(distinct(WeChatArticle.fakeid)))
            )
            total_accounts = total_accounts_result.scalar() or 0
            
            # 今日新增文章数
            today = datetime.now()
            today_start = int(datetime(today.year, today.month, today.day).timestamp())
            today_articles_result = await session.execute(
                select(func.count(WeChatArticle.id)).where(
                    WeChatArticle.add_ts >= today_start * 1000  # add_ts 是毫秒
                )
            )
            today_articles = today_articles_result.scalar() or 0
            
            # 今日新增阅读量
            today_reads_result = await session.execute(
                select(func.sum(WeChatArticle.read_num)).where(
                    WeChatArticle.add_ts >= today_start * 1000
                )
            )
            today_reads = today_reads_result.scalar() or 0
            
            return StatsResponse(
                total_articles=total_articles,
                total_reads=int(total_reads),
                total_likes=int(total_likes),
                total_accounts=total_accounts,
                today_articles=today_articles,
                today_reads=int(today_reads) if today_reads else 0,
            )
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top_articles", response_model=List[TopArticleItem])
async def get_top_articles(
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """
    获取热门文章 Top N（按阅读量排序）
    """
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select, desc
        
        async with get_session() as session:
            query = select(WeChatArticle).order_by(desc(WeChatArticle.read_num)).limit(limit)
            result = await session.execute(query)
            articles = result.scalars().all()
            
            return [
                TopArticleItem(
                    id=article.id,
                    title=article.title or "",
                    account_name=article.account_name or "",
                    read_num=article.read_num or 0,
                    create_time=article.create_time or 0,
                )
                for article in articles
            ]
            
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Get top articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_articles(request: ExportRequest):
    """
    批量导出文章内容（包含图片和CSS资源）
    
    支持格式:
    - html: 导出完整 HTML 文件（包含本地化的图片和CSS）
    - markdown: 转换为 Markdown 格式
    - json: 导出为 JSON 格式（包含元数据）
    
    返回 ZIP 压缩包
    """
    utils.logger.info(f"[WeChatAPI] Export request: {len(request.article_ids)} articles, format: {request.format}")
    
    if not request.article_ids:
        raise HTTPException(status_code=400, detail="请选择要导出的文章")
    
    if len(request.article_ids) > 50:
        raise HTTPException(status_code=400, detail="单次最多导出 50 篇文章（包含资源下载）")
    
    export_format = request.format.lower()
    if export_format not in ["html", "markdown", "json"]:
        raise HTTPException(status_code=400, detail="不支持的导出格式")
    
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select
        import json
        
        async with get_session() as session:
            # 查询文章
            utils.logger.info(f"[WeChatAPI] Querying articles with IDs: {request.article_ids[:5]}{'...' if len(request.article_ids) > 5 else ''}")
            query = select(WeChatArticle).where(WeChatArticle.id.in_(request.article_ids))
            result = await session.execute(query)
            articles = result.scalars().all()
            
            utils.logger.info(f"[WeChatAPI] Found {len(articles)} articles in database")
            
            if not articles:
                raise HTTPException(status_code=404, detail="未找到指定的文章")
            
            # 辅助函数：获取文章内容（支持文件存储和数据库存储）
            async def get_article_content(article) -> str:
                """获取文章内容，优先从文件读取"""
                # 优先从文件读取
                if article.content_path:
                    from tools.content_storage import get_wechat_content_storage
                    storage = get_wechat_content_storage()
                    content = await storage.load_content(article.content_path)
                    if content:
                        return content
                # 回退到数据库内容
                return article.content or ""
            
            # 检查是否有内容（包括文件存储）
            articles_with_content = [a for a in articles if a.content or a.content_path]
            articles_without_content = [a for a in articles if not a.content and not a.content_path]
            utils.logger.info(f"[WeChatAPI] Articles with content: {len(articles_with_content)}, without content: {len(articles_without_content)}")
            
            # 创建 ZIP 文件
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                exported_count = 0
                total_resources = 0
                
                for article_idx, article in enumerate(articles):
                    title = sanitize_filename(article.title or f"article_{article.id}")
                    account = sanitize_filename(article.account_name or "unknown")
                    
                    # 生成目录名
                    date_str = ""
                    if article.create_time:
                        date_str = datetime.fromtimestamp(article.create_time).strftime("%Y%m%d")
                    dir_name = f"{account}/{date_str}_{title}" if date_str else f"{account}/{title}"
                    
                    utils.logger.info(f"[WeChatAPI] Processing article {article_idx + 1}/{len(articles)}: {article.title}")
                    
                    if export_format == "html":
                        # 获取文章内容（支持文件存储）
                        html_content = await get_article_content(article)
                        
                        if html_content:
                            # 先提取资源（从原始 HTML）
                            resources = extract_resources_from_html(html_content)
                            utils.logger.info(f"[WeChatAPI] Found {len(resources)} resources in article")
                            
                            # 下载资源并建立映射
                            url_map: Dict[str, str] = {}
                            for res_url in resources:
                                try:
                                    content, content_type = await download_resource(res_url)
                                    if content:
                                        ext = get_extension_from_url(res_url, content_type)
                                        filename = get_url_hash(res_url) + ext
                                        local_path = f"./assets/{filename}"
                                        
                                        # 写入资源文件
                                        zip_file.writestr(f"{dir_name}/assets/{filename}", content)
                                        url_map[res_url] = local_path
                                        total_resources += 1
                                except Exception as e:
                                    utils.logger.warning(f"[WeChatAPI] Failed to download {res_url}: {e}")
                                
                                # 避免请求过快
                                await asyncio.sleep(0.1)
                            
                            # 清理 HTML 并替换资源路径（参考 wechat-article-exporter）
                            page_content, body_class, css_links = clean_html_for_export(html_content, url_map)
                            
                            # 生成最终 HTML 文档
                            html_document = generate_final_html(
                                title=article.title or '',
                                page_content=page_content,
                                body_class=body_class,
                                css_links=css_links
                            )
                            
                            zip_file.writestr(f"{dir_name}/index.html", html_document.encode('utf-8'))
                            exported_count += 1
                        else:
                            # 没有内容的文章
                            placeholder = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{html.escape(article.title or '')}</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
<h1>{html.escape(article.title or '')}</h1>
<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0;">
    <p style="margin: 0; color: #856404;">⚠️ 该文章内容未被采集</p>
    <p style="margin: 10px 0 0; color: #856404; font-size: 14px;">请在数据管理页面选中该文章，点击"采集内容"按钮重新获取。</p>
</div>
<p>原文链接: <a href="{html.escape(article.link or '')}">{html.escape(article.link or '')}</a></p>
</body></html>"""
                            zip_file.writestr(f"{dir_name}/index.html", placeholder.encode('utf-8'))
                    
                    elif export_format == "markdown":
                        # 获取文章内容（支持文件存储）
                        html_content = await get_article_content(article)
                        
                        if html_content:
                            md_content = html_to_markdown(html_content, article.title)
                            meta = f"""---
title: "{article.title or ''}"
author: "{article.author or ''}"
account: "{article.account_name or ''}"
date: {datetime.fromtimestamp(article.create_time).strftime('%Y-%m-%d %H:%M') if article.create_time else ''}
link: {article.link or ''}
read_num: {article.read_num or 0}
like_num: {article.like_num or 0}
---

"""
                            zip_file.writestr(f"{dir_name}.md", (meta + md_content).encode('utf-8'))
                            exported_count += 1
                        else:
                            placeholder = f"""---
title: "{article.title or ''}"
---

# {article.title or ''}

⚠️ 该文章内容未被采集，请在数据管理页面选中该文章，点击"采集内容"按钮重新获取。

原文链接: {article.link or ''}
"""
                            zip_file.writestr(f"{dir_name}_无内容.md", placeholder.encode('utf-8'))
                    
                    elif export_format == "json":
                        # 获取文章内容（支持文件存储）
                        html_content = await get_article_content(article)
                        
                        article_data = {
                            "id": article.id,
                            "article_id": article.article_id,
                            "title": article.title or "",
                            "author": article.author or "",
                            "account_name": article.account_name or "",
                            "fakeid": article.fakeid or "",
                            "content": html_content,
                            "content_available": bool(html_content),
                            "link": article.link or "",
                            "cover": article.cover or "",
                            "create_time": article.create_time,
                            "create_time_str": datetime.fromtimestamp(article.create_time).strftime('%Y-%m-%d %H:%M:%S') if article.create_time else "",
                            "read_num": article.read_num or 0,
                            "like_num": article.like_num or 0,
                            "comment_count": article.comment_count or 0,
                        }
                        zip_file.writestr(f"{dir_name}.json", json.dumps(article_data, ensure_ascii=False, indent=2).encode('utf-8'))
                        exported_count += 1
                
                # 添加导出说明文件
                readme = f"""# 微信文章导出

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
导出格式: {export_format.upper()}
文章总数: {len(articles)}
有内容文章: {len(articles_with_content)}
无内容文章: {len(articles_without_content)}
下载资源数: {total_resources}

## 文件结构

{"- 每篇文章一个文件夹，包含 index.html 和 assets/ 目录" if export_format == "html" else "- 每篇文章一个文件"}
- 图片和CSS已下载到本地，可离线查看

## 说明

- 文件按公众号分类存放
- 标记"无内容"的文章需要重新采集
- 如需重新采集：在数据管理页面选中文章，点击"采集内容"按钮
"""
                zip_file.writestr("README.txt", readme.encode('utf-8'))
            
            # 返回 ZIP 文件
            zip_buffer.seek(0)
            filename = f"wechat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(articles)}.zip"
            # 中文文件名需要 URL 编码
            filename_cn = f"微信文章导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(articles)}篇.zip"
            filename_encoded = quote(filename_cn)
            
            utils.logger.info(f"[WeChatAPI] Exporting {len(articles)} articles as {export_format}, filename: {filename_cn}")
            
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    # 兼容性：filename 用 ASCII，filename* 用 UTF-8 编码
                    "Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{filename_encoded}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Export articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refetch_content", response_model=RefetchResult)
async def refetch_article_content(request: RefetchRequest):
    """
    重新采集文章内容
    
    根据文章链接重新获取 HTML 内容并更新到数据库
    """
    if not request.article_ids:
        raise HTTPException(status_code=400, detail="请选择要重新采集的文章")
    
    if len(request.article_ids) > 20:
        raise HTTPException(status_code=400, detail="单次最多重新采集 20 篇文章")
    
    utils.logger.info(f"[WeChatAPI] Refetch content request: {len(request.article_ids)} articles")
    
    try:
        from database.db_session import get_session
        from database.models import WeChatArticle
        from sqlalchemy import select
        import asyncio
        
        results = []
        success_count = 0
        failed_count = 0
        
        async with get_session() as session:
            # 查询文章
            query = select(WeChatArticle).where(WeChatArticle.id.in_(request.article_ids))
            result = await session.execute(query)
            articles = result.scalars().all()
            
            if not articles:
                raise HTTPException(status_code=404, detail="未找到指定的文章")
            
            utils.logger.info(f"[WeChatAPI] Found {len(articles)} articles to refetch")
            
            for article in articles:
                article_result = {
                    "id": article.id,
                    "title": article.title or "",
                    "status": "pending",
                    "message": ""
                }
                
                if not article.link:
                    article_result["status"] = "failed"
                    article_result["message"] = "文章链接为空"
                    failed_count += 1
                    results.append(article_result)
                    continue
                
                try:
                    utils.logger.info(f"[WeChatAPI] Fetching content for article {article.id}: {article.link}")
                    
                    # 直接使用 httpx 获取文章内容
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    }
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(article.link, headers=headers, follow_redirects=True)
                        
                        if response.status_code == 200:
                            html_content = response.text
                            
                            # 简单验证 HTML 内容
                            if 'js_content' in html_content or 'rich_media_content' in html_content:
                                # 检查是否启用文件存储
                                from config import wechat_config
                                enable_file_storage = getattr(wechat_config, 'ENABLE_CONTENT_FILE_STORAGE', True)
                                
                                if enable_file_storage:
                                    # 存储到本地文件
                                    from tools.content_storage import get_wechat_content_storage
                                    storage = get_wechat_content_storage()
                                    content_path = await storage.save_content(
                                        article.article_id, 
                                        html_content, 
                                        article.fakeid or ""
                                    )
                                    if content_path:
                                        article.content_path = content_path
                                        article.content = ""  # 清空数据库中的内容
                                        utils.logger.info(f"[WeChatAPI] Content saved to file: {content_path}")
                                    else:
                                        # 文件存储失败，回退到数据库
                                        article.content = html_content
                                else:
                                    # 直接存储到数据库
                                    article.content = html_content
                                
                                article.last_modify_ts = int(datetime.now().timestamp() * 1000)
                                
                                article_result["status"] = "success"
                                article_result["message"] = "内容采集成功"
                                success_count += 1
                                utils.logger.info(f"[WeChatAPI] Successfully fetched content for article {article.id}")
                            elif '该内容已被发布者删除' in html_content:
                                article_result["status"] = "failed"
                                article_result["message"] = "文章已被删除"
                                failed_count += 1
                            elif '此内容因违规无法查看' in html_content:
                                article_result["status"] = "failed"
                                article_result["message"] = "文章因违规无法查看"
                                failed_count += 1
                            else:
                                article_result["status"] = "failed"
                                article_result["message"] = "无法识别文章内容"
                                failed_count += 1
                        else:
                            article_result["status"] = "failed"
                            article_result["message"] = f"HTTP {response.status_code}"
                            failed_count += 1
                            
                except Exception as e:
                    utils.logger.error(f"[WeChatAPI] Error fetching article {article.id}: {e}")
                    article_result["status"] = "failed"
                    article_result["message"] = str(e)
                    failed_count += 1
                
                results.append(article_result)
                
                # 避免请求过快
                await asyncio.sleep(1)
            
            # 提交数据库更改
            await session.commit()
            utils.logger.info(f"[WeChatAPI] Refetch completed: {success_count} success, {failed_count} failed")
        
        return RefetchResult(
            success=success_count,
            failed=failed_count,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"[WeChatAPI] Refetch content failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

