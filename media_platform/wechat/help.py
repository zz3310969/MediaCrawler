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

from urllib.parse import parse_qs, urlparse
from typing import Optional, Dict


def extract_article_url_params(url: str) -> Optional[Dict[str, str]]:
    """
    从微信文章URL中提取参数
    
    Args:
        url: 微信文章URL
        
    Returns:
        包含 __biz, mid, idx, sn 等参数的字典
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        result = {}
        for key in ['__biz', 'mid', 'idx', 'sn', 'scene', 'subscene']:
            if key in params:
                result[key] = params[key][0]
        
        return result if result else None
    except Exception:
        return None


def extract_fakeid_from_url(url: str) -> Optional[str]:
    """
    从公众号主页URL中提取fakeid
    
    Args:
        url: 公众号主页URL
        
    Returns:
        fakeid字符串
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if '__biz' in params:
            return params['__biz'][0]
        elif 'fakeid' in params:
            return params['fakeid'][0]
        
        return None
    except Exception:
        return None


def format_article_list_response(response_data: Dict) -> Dict:
    """
    格式化文章列表API响应数据
    
    Args:
        response_data: API原始响应
        
    Returns:
        格式化后的文章列表
    """
    try:
        if response_data.get('base_resp', {}).get('ret') != 0:
            return {'articles': [], 'total': 0, 'error': response_data.get('base_resp', {}).get('err_msg', 'Unknown error')}
        
        articles = response_data.get('articles', [])
        total = response_data.get('total_count', 0)
        
        return {
            'articles': articles,
            'total': total,
            'error': None
        }
    except Exception as e:
        return {'articles': [], 'total': 0, 'error': str(e)}


def clean_html_content(html: str) -> str:
    """
    清理HTML内容，移除脚本和样式标签
    
    Args:
        html: 原始HTML内容
        
    Returns:
        清理后的HTML
    """
    import re
    
    # 移除script标签
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除style标签
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html

